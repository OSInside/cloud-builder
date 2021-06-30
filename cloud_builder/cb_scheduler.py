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
           [--package-limit=<number>]

options:
    --update-interval=<time_sec>
        Optional update interval for the lookup of the
        kafka cb_request topic. Default is 30sec

    --package-limit=<number>
        Max number of package builds this scheduler handles
        at the same time. Default is 10
"""
import os
import platform
import psutil
import signal
from docopt import docopt
from textwrap import dedent
from cloud_builder.version import __version__
from cloud_builder.cloud_logger import CBCloudLogger
from cloud_builder.exceptions import exception_handler
from cloud_builder.defaults import Defaults
from cloud_builder.kafka import CBKafka
from kiwi.command import Command
from kiwi.privileges import Privileges
from kiwi.path import Path
from apscheduler.schedulers.background import BlockingScheduler
from typing import Dict

running_builds = 0
running_limit = 10


@exception_handler
def main() -> None:
    # TODO: docstring incomplete
    """
    Each distribution target for the package needs to get
    configured as a profile in the cloud_builder.kiwi such that
    the package can be build for different distributions and
    architectures. The profiles which actually references the
    distribution becomes effective when listed in the

        cloud_builder.yml

    metadata file under the distributions tag. This file is
    used to configure general build parameters for the package
    and typically looks like the following example:

    .. code:: yaml
        name: xclock

        distributions:
          -
            profile: TW
            arch: x86_64
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

    if args['--package-limit']:
        global running_limit
        running_limit = int(args['--package-limit'])

    repeat_timeout = int(args['--update-interval'] or 30)

    handle_build_requests(
        request_timeout=repeat_timeout - 1
    )

    project_scheduler = BlockingScheduler()
    project_scheduler.add_job(
        lambda: handle_build_requests(request_timeout=repeat_timeout - 1),
        'interval', seconds=repeat_timeout
    )
    project_scheduler.start()


def handle_build_requests(request_timeout) -> None:
    global running_builds
    global running_limit

    log = CBCloudLogger('CBScheduler', '(system)')

    if get_running_builds() < running_limit:
        kafka = CBKafka(config_file=Defaults.get_kafka_config())
        try:
            for message in kafka.read('cb-request', timeout_ms=request_timeout):
                request = kafka.validate_request(message.value)
                if request['arch'] == platform.machine():
                    log.response(
                        {'message': 'Accept package build request', **request}
                    )
                    kafka.acknowledge()
                    build_package(request)
                else:
                    # do not acknowledge/build if the host architecture
                    # does not match the package. The request stays in
                    # the topic to be presented for other schedulers
                    log.warning(
                        'Cannot build package: "{0}" for "{1}" on "{2}"'.format(
                            request['package'],
                            request['arch'],
                            platform.machine()
                        )
                    )
        finally:
            log.info('Closing kafka connection')
            kafka.close()
    else:
        # runner is busy
        log.response(
            {
                'message': 'Max running builds limit reached'
            }
        )


def build_package(request: Dict) -> None:
    log = CBCloudLogger(
        'CBScheduler', os.path.basename(request['package'])
    )
    package_source_path = os.path.join(
        Defaults.get_runner_project_dir(), format(request['package'])
    )
    if check_package_sources(package_source_path, log):
        package_config = Defaults.get_package_config(
            package_source_path
        )
        reset_build_if_running(package_config, log)

        status_flags = Defaults.get_status_flags()
        if request['action'] == status_flags.package_changed:
            log.info('Update project git source repo prior build')
            Command.run(
                ['git', '-C', Defaults.get_runner_project_dir(), 'pull']
            )

        log.info('Starting build process')
        Command.run(
            [
                'bash', create_run_script(
                    package_config, package_source_path
                )
            ]
        )


def reset_build_if_running(
    package_config: Dict, log: CBCloudLogger
) -> None:
    package_root = os.path.join(
        Defaults.get_runner_package_root(), package_config['name']
    )
    package_run_pid = f'{package_root}.pid'
    if os.path.isfile(package_run_pid):
        with open(package_run_pid) as pid_fd:
            build_pid = int(pid_fd.read().strip())
        log.info(
            'Checking state of former build with PID:{0}'.format(
                build_pid
            )
        )
        if psutil.pid_exists(build_pid):
            log.response(
                {
                    'message':
                        'Stop jobs associated with PID:{0} for rebuild'.format(
                            build_pid
                        )
                }
            )
            os.kill(build_pid, signal.SIGTERM)


def get_running_builds() -> int:
    # TODO: lookup current running limit
    return 0


def check_package_sources(
    package_source_path: str, log: CBCloudLogger
) -> bool:
    if not os.path.isdir(package_source_path):
        log.response(
            {
                'message': f'Package does not exist: {package_source_path}'
            }
        )
        return False

    # TODO: Also check for meta data files (.kiwi and cloud_builder.yml)
    return True


def create_run_script(
    package_config: Dict, package_source_path: str
) -> str:
    package_root = os.path.join(
        Defaults.get_runner_package_root(), package_config['name']
    )
    run_script = dedent('''
        #!/bin/bash

        set -e

        function finish {
            kill $(jobs -p) &>/dev/null
        }

        {
        trap finish EXIT
    ''')
    for target in package_config.get('distributions') or []:
        if target['arch'] == platform.machine():
            dist_profile = f'{target["profile"]}.{target["arch"]}'
            run_script += dedent('''
                cb-prepare --root {runner_root} \\
                    --package {package_source_path} --profile {dist_profile}
                cb-run --root {target_root} &> {target_root}.log
            ''').format(
                runner_root=Defaults.get_runner_package_root(),
                package_source_path=package_source_path,
                dist_profile=dist_profile,
                target_root=os.path.join(f'{package_root}@{dist_profile}')
            )
    run_script += dedent('''
        }} &>{package_root}.log &

        echo $! > {package_root}.pid
    ''').format(
        package_root=package_root
    )
    package_run_script = f'{package_root}.sh'
    with open(package_run_script, 'w') as script:
        script.write(run_script)
    return package_run_script
