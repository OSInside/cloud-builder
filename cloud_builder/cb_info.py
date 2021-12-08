# Copyright (c) 2021 Marcus Schaefer.  All rights reserved.
#
# This file is part of Cloud Builder.
#
# Cloud Builder is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Cloud Builder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Cloud Builder.  If not, see <http://www.gnu.org/licenses/>
#
"""
usage: cb-info -h | --help
       cb-info
           [--update-interval=<time_sec>]
           [--poll-timeout=<time_msec>]
           [--respond-always]

options:
    --update-interval=<time_sec>
        Optional update interval to reconnect to the
        message broker. Default is 10sec

    --poll-timeout=<time_msec>
        Optional message broker poll timeout to return if no
        requests are available. Default: 5000msec

    --respond-always
        Always respond even if there is no information
        available for the requested package/image
"""
import os
import psutil
from typing import (
    Any, Optional
)
from datetime import datetime
from docopt import docopt
from cloud_builder.version import __version__
from cloud_builder.broker import CBMessageBroker
from cloud_builder.info_response.info_response import CBInfoResponse
from cloud_builder.identity import CBIdentity
from cloud_builder.cloud_logger import CBCloudLogger
from cloud_builder.defaults import Defaults
from kiwi.privileges import Privileges
from apscheduler.schedulers.background import BlockingScheduler

from cloud_builder.exceptions import (
    exception_handler,
    CBSchedulerIntervalError
)

INFO_INSTANCES: int = 0


@exception_handler
def main() -> None:
    """
    cb-info - lookup package/image information. The package/image
    builds on a runner contains a number of files like
    the following example:

    /var/tmp/CB/projects/PROJECT/
       ├── package@DIST.ARCH/
       ├── package@DIST.ARCH.build.log
       ├── package@DIST.ARCH.pid
       ├── package@DIST.ARCH.prepare.log
       ├── package@DIST.ARCH.result.yml
       ├── package@DIST.ARCH.run.log
       ├── package@DIST.ARCH.sh
       ├── package@DIST.ARCH.solver.json
       ├── ...
       ├── image@SELECTION.ARCH/
       ├── image@SELECTION.ARCH.build.log
       ├── image@SELECTION.ARCH.pid
       ├── image@SELECTION.ARCH.result.yml
       ├── image@SELECTION.ARCH.sh
       └── image@SELECTION.ARCH.solver.json

    The local file information is used to construct
    a response record with information about the
    package/image build:
    """
    args = docopt(
        __doc__,
        version='CB (info) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()

    log = CBCloudLogger('CBInfo', '(system)')
    log.set_logfile()

    update_interval = int(args['--update-interval'] or 10)
    poll_timeout = int(args['--poll-timeout'] or 5000)
    respond_always = args['--respond-always']

    if poll_timeout / 1000 > update_interval:
        # This should not be allowed, as the BlockingScheduler would
        # just create unnneded threads and new consumers which could
        # cause an expensive rebalance on the message broker
        raise CBSchedulerIntervalError(
            'Poll timeout on the message broker greater than update interval'
        )

    handle_info_requests(poll_timeout, respond_always, log)

    project_scheduler = BlockingScheduler()
    project_scheduler.add_job(
        lambda: handle_info_requests(poll_timeout, respond_always, log),
        'interval', seconds=update_interval
    )
    project_scheduler.start()


def handle_info_requests(
    poll_timeout: int, respond_always: bool, log: CBCloudLogger
) -> None:
    """
    Listen to the message broker queue for info requests
    in pub/sub mode. The subscription model is based on
    group_id == IP address of the host running the cb-info
    service. This way every info service is assigned to a
    unique group and will receive the request.

    The package information from the request is checked
    if this host has built / or is building the requested
    package such that information about it can be produced.
    In case the package build information is found on this
    host the info service acknowledges the request and
    sends a response to the message broker queue for
    info responses

    :param int poll_timeout:
        timeout in msec after which the blocking read() to the
        message broker returns
    """
    global INFO_INSTANCES
    if INFO_INSTANCES != 0:
        log.info('Info server already running')
        return

    broker = CBMessageBroker.new(
        'kafka', config_file=Defaults.get_broker_config()
    )
    INFO_INSTANCES += 1
    try:
        while(True):
            for message in broker.read(
                topic=Defaults.get_info_request_queue_name(),
                group=CBIdentity.get_external_ip(),
                timeout_ms=poll_timeout
            ):
                request = broker.validate_info_request(message.value)
                if request:
                    if 'package' in request:
                        arch = request['package']['arch']
                        dist = request['package']['dist']
                        lookup_package(
                            request['project'], arch, dist,
                            request['request_id'], respond_always,
                            broker, log
                        )
                    elif 'image' in request:
                        arch = request['image']['arch']
                        selection = request['image']['selection']
                        lookup_image(
                            request['project'], arch, selection,
                            request['request_id'], respond_always,
                            broker, log
                        )
    finally:
        log.info('Closing message broker connection')
        INFO_INSTANCES -= 1
        broker.close()


def lookup_image(
    image: str, arch: str, selection: str, request_id: str,
    respond_always: bool, broker: Any, log: CBCloudLogger
) -> None:
    log.set_id(image)
    build_pid_file = os.sep.join(
        [Defaults.get_runner_root(), f'{image}@{selection}.{arch}.pid']
    )
    if os.path.isfile(build_pid_file):
        broker.acknowledge()

    source_ip = log.get_id().split(':')[1]
    utc_modification_time = get_result_modification_time(
        build_pid_file
    )
    image_file_base_name = os.sep.join(
        [
            Defaults.get_runner_root(),
            f'{image}@{selection}.{arch}'
        ]
    )
    image_result_file = image_file_base_name + '.result.yml'
    image_build_log_file = image_file_base_name + '.build.log'
    image_solver_file = image_file_base_name + '.solver.json'
    image_binaries = []
    image_status = get_image_status()
    if os.path.isfile(image_result_file):
        with open(image_result_file) as result_file:
            result = broker.validate_build_response(result_file.read())
            image_binaries = result['image']['binary_packages']
            image_status = get_image_status(result['response_code'])

    if os.path.isfile(build_pid_file) or respond_always:
        response = CBInfoResponse(
            request_id, log.get_id()
        )
        response.set_image_info_response(
            image, source_ip, is_building(build_pid_file), arch, selection
        )
        response.set_image_info_response_result(
            image_binaries,
            image_build_log_file if os.path.isfile(
                image_build_log_file
            ) else 'none',
            image_solver_file if os.path.isfile(
                image_solver_file
            ) else 'none',
            format(utc_modification_time or 'none'),
            image_status
        )
        log.info_response(response, broker)


def lookup_package(
    package: str, arch: str, dist: str, request_id: str,
    respond_always: bool, broker: Any, log: CBCloudLogger
) -> None:
    log.set_id(package)
    build_pid_file = os.sep.join(
        [Defaults.get_runner_root(), f'{package}@{dist}.{arch}.pid']
    )
    if os.path.isfile(build_pid_file):
        broker.acknowledge()

    source_ip = log.get_id().split(':')[1]
    utc_modification_time = get_result_modification_time(
        build_pid_file
    )
    package_file_base_name = os.sep.join(
        [
            Defaults.get_runner_root(),
            f'{package}@{dist}.{arch}'
        ]
    )
    package_result_file = package_file_base_name + '.result.yml'
    package_prepare_log_file = package_file_base_name + '.prepare.log'
    package_build_log_file = package_file_base_name + '.build.log'
    package_solver_file = package_file_base_name + '.solver.json'
    package_binaries = []
    package_status = get_package_status()
    if os.path.isfile(package_result_file):
        with open(package_result_file) as result_file:
            result = broker.validate_build_response(result_file.read())
            package_binaries = result['package']['binary_packages']
            package_status = get_package_status(result['response_code'])

    if os.path.isfile(build_pid_file) or respond_always:
        response = CBInfoResponse(
            request_id, log.get_id()
        )
        response.set_package_info_response(
            package, source_ip, is_building(build_pid_file), arch, dist
        )
        response.set_package_info_response_result(
            package_binaries,
            package_prepare_log_file if os.path.isfile(
                package_prepare_log_file
            ) else 'none',
            package_build_log_file if os.path.isfile(
                package_build_log_file
            ) else 'none',
            package_solver_file if os.path.isfile(
                package_solver_file
            ) else 'none',
            format(utc_modification_time or 'none'),
            package_status
        )
        log.info_response(response, broker)


def get_result_modification_time(filename: str) -> Optional[datetime]:
    if os.path.exists(filename):
        return datetime.utcfromtimestamp(
            os.path.getmtime(filename)
        )
    return None


def get_package_status(response_code: str = '') -> str:
    status_flags = Defaults.get_status_flags()
    if response_code == status_flags.package_build_succeeded:
        return status_flags.package_build_succeeded
    elif response_code == status_flags.package_build_failed:
        return status_flags.package_build_failed
    else:
        return 'unknown'


def get_image_status(response_code: str = '') -> str:
    status_flags = Defaults.get_status_flags()
    if response_code == status_flags.image_build_succeeded:
        return status_flags.image_build_succeeded
    elif response_code == status_flags.image_build_failed:
        return status_flags.image_build_failed
    else:
        return 'unknown'


def is_building(pidfile: str) -> bool:
    if os.path.isfile(pidfile):
        with open(pidfile) as pid_fd:
            build_pid = int(pid_fd.read())
            if psutil.pid_exists(build_pid):
                return True
    return False
