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

options:
    --update-interval=<time_sec>
        Optional update interval to reconnect to the
        message broker. Default is 10sec

    --poll-timeout=<time_msec>
        Optional message broker poll timeout to return if no
        requests are available. Default: 5000msec
"""
import os
import psutil
from typing import Any
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


@exception_handler
def main() -> None:
    """
    cb-info - lookup package information. The package
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
       └── package@DIST.ARCH.solver.json

    The local file information is used to construct
    a response record with information about the
    package build:
    """
    args = docopt(
        __doc__,
        version='CB (info) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()

    update_interval = int(args['--update-interval'] or 10)
    poll_timeout = int(args['--poll-timeout'] or 5000)

    if poll_timeout / 1000 > update_interval:
        # This should not be allowed, as the BlockingScheduler would
        # just create unnneded threads and new consumers which could
        # cause an expensive rebalance on the message broker
        raise CBSchedulerIntervalError(
            'Poll timeout on the message broker greater than update interval'
        )

    handle_info_requests(poll_timeout)

    project_scheduler = BlockingScheduler()
    project_scheduler.add_job(
        lambda: handle_info_requests(poll_timeout),
        'interval', seconds=update_interval
    )
    project_scheduler.start()


def handle_info_requests(poll_timeout: int) -> None:
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
    log = CBCloudLogger('CBInfo', '(system)')

    broker = CBMessageBroker.new(
        'kafka', config_file=Defaults.get_broker_config()
    )
    try:
        while(True):
            for message in broker.read(
                topic=Defaults.get_info_request_queue_name(),
                group=CBIdentity.get_external_ip(),
                timeout_ms=poll_timeout
            ):
                request = broker.validate_info_request(message.value)
                if request:
                    lookup(
                        request['package'],
                        request['arch'],
                        request['dist'],
                        request['request_id'],
                        broker
                    )
    finally:
        log.info('Closing message broker connection')
        broker.close()


def lookup(package: str, arch: str, dist: str, request_id: str, broker: Any):
    log = CBCloudLogger('CBInfo', package)
    build_pid_file = os.sep.join(
        [Defaults.get_runner_package_root(), f'{package}@{dist}.{arch}.pid']
    )
    if os.path.isfile(build_pid_file):
        broker.acknowledge()
        source_ip = log.get_id().split(':')[1]
        response = CBInfoResponse(
            request_id, log.get_id()
        )
        response.set_info_response(
            package, source_ip, is_building(build_pid_file), arch, dist
        )
        package_result_file = os.sep.join(
            [
                Defaults.get_runner_package_root(),
                f'{package}@{dist}.{arch}.result.yml'
            ]
        )
        if os.path.isfile(package_result_file):
            utc_modification_time = get_result_modification_time(
                package_result_file
            )
            with open(package_result_file) as result_file:
                result = broker.validate_package_response(result_file.read())
                response.set_info_response_result(
                    result['binary_packages'],
                    result['prepare_log_file'],
                    result['log_file'],
                    result['solver_file'],
                    format(utc_modification_time),
                    get_package_status(result['response_code'])
                )
        log.info_response(response, broker)


def get_result_modification_time(filename: str) -> datetime:
    return datetime.utcfromtimestamp(
        os.path.getmtime(filename)
    )


def get_package_status(response_code: str) -> str:
    status_flags = Defaults.get_status_flags()
    if response_code == status_flags.package_build_succeeded:
        return status_flags.package_build_succeeded
    elif response_code == status_flags.package_build_failed:
        return status_flags.package_build_failed
    elif response_code == status_flags.package_build_running:
        return status_flags.package_build_running
    else:
        return 'unknown'


def is_building(pidfile: str) -> bool:
    with open(pidfile) as pid_fd:
        build_pid = int(pid_fd.read())
        if psutil.pid_exists(build_pid):
            return True
    return False
