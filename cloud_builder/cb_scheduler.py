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
usage: cb-scheduler -h | --help
       cb-scheduler
           [--update-interval=<time_sec>]
           [--poll-timeout=<time_msec>]
           [--package-limit=<number>]

options:
    --update-interval=<time_sec>
        Optional update interval to reconnect to the
        message broker. Default is 10sec

    --poll-timeout=<time_msec>
        Optional message broker poll timeout to return if no
        requests are available. Default: 5000msec

    --package-limit=<number>
        Max number of package builds this scheduler handles
        at the same time. Default: 10
"""
import os
import platform
import psutil
import signal
from docopt import docopt
from textwrap import dedent
from cloud_builder.version import __version__
from cloud_builder.cloud_logger import CBCloudLogger
from cloud_builder.response.response import CBResponse
from cloud_builder.defaults import Defaults
from cloud_builder.package_metadata.package_metadata import CBPackageMetaData
from cloud_builder.broker import CBMessageBroker
from kiwi.command import Command
from kiwi.privileges import Privileges
from kiwi.path import Path
from apscheduler.schedulers.background import BlockingScheduler
from typing import (
    Dict, Any
)

from cloud_builder.exceptions import (
    exception_handler,
    CBSchedulerIntervalError
)


@exception_handler
def main() -> None:
    """
    cb-scheduler - listens on incoming package build requests
    from the message broker on a regular schedule. Only if
    the max package to build limit is not exceeded, request
    messages from the broker are accepted. In case the request
    matches the runner capabilities e.g architecture it gets
    acknowledged and removed from the broker queue.

    A package can be build for different distribution targets
    and architectures. Each distribution target/arch needs to
    be configured as a profile in the .kiwi metadata and added
    as effective build target in the package configuration file:

        Defaults.get_cloud_builder_metadata_file_name()

    An example package config to build the xclock package
    for the Tumbleweed distribution for x86_64 and aarch64
    would look like the following:

    .. code:: yaml

        schema_version: 0.1
        name: xclock

        distributions:
          -
            dist: TW
            arch: x86_64
            runner_group: suse

          -
            dist: TW
            arch: aarch64
            runner_group: suse

    The above instructs the scheduler to create two buildroot
    environments, one for Tumbleweed(x86_64) and one for
    Tumbleweed(aarch64) and build the xclock package in each
    of these buildroots. To process this properly the scheduler
    creates a script which calls cb-prepare followed by cb-run
    with the corresponding parameters for each element of the
    distributions list. Each dist.arch build process is triggered
    by one build request. In the above example two requests
    to build all targets in the distributions list would be
    required.

    The dist and arch settings of a distribution are combined
    into profile names given to cb-prepare as parameter and used
    in KIWI to create the buildroot environment. From the above
    example this would lead to two profiles named:

    * TW.x86_64
    * TW.aarch64

    The .kiwi metadata file has to provide instructions
    such that the creation of a correct buildroot for these
    profiles is possible.
    """
    args = docopt(
        __doc__,
        version='CB (scheduler) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()

    Path.create(
        Defaults.get_runner_package_root()
    )

    running_limit = int(args['--package-limit'] or 10)
    update_interval = int(args['--update-interval'] or 10)
    poll_timeout = int(args['--poll-timeout'] or 5000)

    if poll_timeout / 1000 > update_interval:
        # This should not be allowed, as the BlockingScheduler would
        # just create unnneded threads and new consumers which could
        # cause an expensive rebalance on the message broker
        raise CBSchedulerIntervalError(
            'Poll timeout on the message broker greater than update interval'
        )

    handle_build_requests(poll_timeout, running_limit)

    project_scheduler = BlockingScheduler()
    project_scheduler.add_job(
        lambda: handle_build_requests(poll_timeout, running_limit),
        'interval', seconds=update_interval
    )
    project_scheduler.start()


def handle_build_requests(poll_timeout: int, running_limit: int) -> None:
    """
    Check on the runner state and if ok listen to the
    message broker queue for new package build requests
    The package_request_queue is used as shared queue
    within a single group. It's important to have this
    queue configured to distribute messages across
    several readers to let multiple CB scheduler scale

    :param int poll_timeout:
        timeout in msec after which the blocking read() to the
        message broker returns
    :param int running_limit:
        allow up to running_limit package builds at the same time.
        If exceeded an eventual connection to the message broker
        will be closed and opened again if the limit is no
        longer reached
    """
    log = CBCloudLogger('CBScheduler', '(system)')

    if get_running_builds() >= running_limit:
        # runner is busy...
        log.info('Max running builds limit reached')
        return

    broker = CBMessageBroker.new(
        'kafka', config_file=Defaults.get_broker_config()
    )
    try:
        while(True):
            if get_running_builds() >= running_limit:
                # runner is busy...
                log.info('Max running builds limit reached')
                break
            for message in broker.read(
                topic=broker.get_runner_group(), timeout_ms=poll_timeout
            ):
                request = broker.validate_package_request(message.value)
                if request:
                    package_source_path = os.path.join(
                        Defaults.get_runner_project_dir(),
                        format(request['package'])
                    )
                    package_config = is_request_valid(
                        package_source_path, request, log, broker
                    )
                    if package_config:
                        build_package(request, broker, package_config)
    finally:
        log.info('Closing message broker connection')
        broker.close()


def build_package(
    request: Dict, broker: CBMessageBroker, package_config: Dict
) -> None:
    """
    Update the package sources and run the script which
    utilizes cb-prepare/cb-run to build the package for
    all configured targets

    :param dict request: yaml dict request record
    :param CBMessageBroker broker: instance of CBMessageBroker
    :param dict package_config: yaml dict package metadata
    """
    log = CBCloudLogger(
        'CBScheduler', os.path.basename(request['package'])
    )
    reset_build_if_running(
        request, log, broker
    )
    status_flags = Defaults.get_status_flags()
    if request['action'] == status_flags.package_rebuild or \
       request['action'] == status_flags.package_rebuild_clean or \
       request['action'] == status_flags.package_source_rebuild or \
       request['action'] == status_flags.package_source_rebuild_clean:
        log.info('Update project git source repo prior build')
        Command.run(
            ['git', '-C', Defaults.get_runner_project_dir(), 'pull']
        )

    buildroot_rebuild = False
    if request['action'] == status_flags.package_source_rebuild_clean or \
       request['action'] == status_flags.package_rebuild_clean:
        buildroot_rebuild = True

    log.info('Starting build process')
    Command.run(
        ['bash', create_run_script(request, buildroot_rebuild)]
    )


def reset_build_if_running(
    request: Dict, log: CBCloudLogger, broker: CBMessageBroker
) -> None:
    """
    Check if the same package/arch is currently/still running
    and kill the process associated with it

    :param dict request: yaml dict request record
    :param CBCloudLogger log: logger instance
    :param CBMessageBroker broker: instance of CBMessageBroker
    """
    package_root = os.path.join(
        Defaults.get_runner_package_root(), request['package']
    )
    dist_profile = f'{request["dist"]}.{request["arch"]}'
    target_root = f'{package_root}@{dist_profile}'
    package_run_pid = f'{target_root}.pid'
    if os.path.isfile(package_run_pid):
        with open(package_run_pid) as pid_fd:
            build_pid = int(pid_fd.read().strip())
        log.info(
            'Checking state of former build with PID:{0}'.format(
                build_pid
            )
        )
        if psutil.pid_exists(build_pid):
            status_flags = Defaults.get_status_flags()
            response = CBResponse(request['request_id'], log.get_id())
            response.set_package_jobs_reset_response(
                message='Kill job group for PID:{0} prior rebuild'.format(
                    build_pid
                ),
                response_code=status_flags.reset_running_build,
                package=request['package'],
                arch=request['arch'],
                dist=request['dist']
            )
            log.response(response, broker)
            os.kill(build_pid, signal.SIGTERM)


def get_running_builds() -> int:
    """
    Lookup the process table for running builds

    :return: Number of running build processes

    :rtype: int
    """
    # TODO: lookup current running limit
    return 0


def is_request_valid(
    package_source_path: str, request: Dict, log: CBCloudLogger, broker: Any
) -> Dict:
    """
    Sanity checks between the request and the package sources

    1. Check if given package source exists
    2. Check if there is a cloud builder metadata and kiwi file
    3. Check if architecture + dist + runner_group is configured in the metadata
    4. Check if the host architecture is compatbile with the
       request architecture

    :param str package_source_path: path to package sources
    :param dict request: yaml dict request record
    :param CBCloudLogger log: logger instance
    :param CBMessageBroker broker: instance of CBMessageBroker

    :return: metadata config dict

    :rtype: dict
    """
    status_flags = Defaults.get_status_flags()
    response = CBResponse(
        request['request_id'], log.get_id()
    )
    # 1. Check on package sources to exist
    if not os.path.isdir(package_source_path):
        response.set_package_not_existing_response(
            message=f'Package does not exist: {package_source_path}',
            response_code=status_flags.package_not_existing,
            package=request['package']
        )
        log.response(response, broker)
        return {}

    # 2. Check on package metadata to exist
    package_metadata = os.path.join(
        package_source_path, Defaults.get_cloud_builder_metadata_file_name()
    )
    if not os.path.isfile(package_metadata):
        response.set_package_metadata_not_existing_response(
            message=f'Package metadata does not exist: {package_metadata}',
            response_code=status_flags.package_metadata_not_existing,
            package=request['package']
        )
        log.response(response, broker)
        return {}

    # 3. Check if requested arch+dist is configured
    target_ok = False
    request_arch = request['arch']
    request_dist = request['dist']
    request_runner_group = request['runner_group']
    package_config = CBPackageMetaData.get_package_config(
        package_source_path, log, request['request_id']
    )
    if package_config:
        for target in package_config.get('distributions') or []:
            if request_arch == target.get('arch') and \
               request_dist == target.get('dist') and \
               request_runner_group == target.get('runner_group'):
                target_ok = True
                break
    if not target_ok:
        response.set_package_invalid_target_response(
            message='No build config for: {0}.{1} in runner group {2}'.format(
                request_dist, request_arch, request_runner_group
            ),
            response_code=status_flags.package_target_not_configured,
            package=request['package']
        )
        log.response(response, broker)
        return {}

    # 4. Check if host architecture is compatbile
    if not request['arch'] == platform.machine():
        response.set_buildhost_arch_incompatible_response(
            message=f'Incompatible arch: {platform.machine()}',
            response_code=status_flags.package_request_accepted,
            package=request['package']
        )
        log.response(response, broker)
        return {}

    # All good...
    response.set_package_build_scheduled_response(
        message='Accept package build request',
        response_code=status_flags.package_request_accepted,
        package=request['package'],
        arch=request['arch'],
        dist=request['dist']
    )
    log.response(response, broker)
    broker.acknowledge()
    return package_config


def create_run_script(request: Dict, buildroot_rebuild: bool) -> str:
    """
    Create script to call cb-prepare followed by cb-run
    for each configured distribution/arch

    :param dict request: yaml dict request record
    :param bool buildroot_rebuild: rebuild buildroot True|False

    :return: file path name for script

    :rtype: str
    """
    package_source_path = os.path.join(
        Defaults.get_runner_project_dir(), request['package']
    )
    package_root = os.path.join(
        Defaults.get_runner_package_root(), request['package']
    )
    dist_profile = f'{request["dist"]}.{request["arch"]}'
    target_root = f'{package_root}@{dist_profile}'
    run_script = dedent('''
        #!/bin/bash

        set -e

        rm -f {target_root}.log

        if {buildroot_rebuild}; then
            rm -rf {target_root}
        fi

        function finish {{
            kill $(jobs -p) &>/dev/null
        }}

        {{
            trap finish EXIT
            cb-prepare --root {runner_root} \\
                --package {package_source_path} \\
                --profile {dist_profile} \\
                --request-id {request_id}
            cb-run --root {target_root} &> {target_root}.build.log \\
                --request-id {request_id}
        }} &>>{target_root}.run.log &

        echo $! > {target_root}.pid
    ''').format(
        buildroot_rebuild='true' if buildroot_rebuild else 'false',
        runner_root=Defaults.get_runner_package_root(),
        package_source_path=package_source_path,
        dist_profile=dist_profile,
        target_root=target_root,
        request_id=request['request_id']
    )
    package_run_script = f'{target_root}.sh'
    Path.create(os.path.dirname(package_run_script))
    with open(package_run_script, 'w') as script:
        script.write(run_script)
    return package_run_script
