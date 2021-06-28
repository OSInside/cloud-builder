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
import psutil
import signal
from docopt import docopt
from textwrap import dedent
from cloud_builder.version import __version__
from cloud_builder.logger import CBLogger
from cloud_builder.exceptions import exception_handler
from cloud_builder.defaults import Defaults
from cloud_builder.kafka import CBKafka
from cloud_builder.identity import CBIdentity
from kiwi.command import Command
from kiwi.privileges import Privileges
from kiwi.path import Path
from apscheduler.schedulers.background import BlockingScheduler
from typing import Dict

log = CBLogger.get_logger()

CBLogger.set_logfile(
    Defaults.get_cb_logfile()
)

ID = CBIdentity.get_id('CBScheduler')

running_builds = 0
running_limit = 10


@exception_handler
def main() -> None:
    args = docopt(
        __doc__,
        version='CB (scheduler) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()

    if args['--package-limit']:
        global running_limit
        running_limit = int(args['--package-limit'])

    handle_build_requests()

    project_scheduler = BlockingScheduler()
    project_scheduler.add_job(
        lambda: handle_build_requests(),
        'interval', seconds=int(args['--update-interval'] or 30)
    )
    project_scheduler.start()


def handle_build_requests() -> None:
    global running_builds
    global running_limit

    kafka = CBKafka(config_file=Defaults.get_kafka_config())
    kafka_request_list = kafka.read_request()

    if kafka_request_list:
        # TODO: lookup current running limit

        if running_builds <= running_limit:
            kafka.acknowledge()
            kafka.close()
        else:
            # Do not acknowledge if running_limit is exceeded.
            # The request will stay in the queue and gets
            # handled by another runner or this one if the
            # limit is no longer exceeded
            # TODO: send this information to kafka(cb-response)
            kafka.close()
            return

        for request in kafka_request_list:
            build_package(request)


def build_package(request: Dict) -> None:
    status_flags = Defaults.get_status_flags()
    package_path = os.path.join(
        Defaults.get_runner_project_dir(), format(request['package'])
    )
    # TODO: check package location and send error to kafka(cb-response)
    package_config = Defaults.get_package_config(
        package_path
    )
    cb_root = Defaults.get_runner_package_root()
    Path.create(cb_root)
    package_root = os.path.join(
        cb_root, f'{package_config["name"]}'
    )
    package_run_script = f'{package_root}.sh'

    package_run_pid = f'{package_root}.pid'
    if os.path.isfile(package_run_pid):
        with open(package_run_pid) as pid_fd:
            build_pid = int(pid_fd.read().strip())
        log.info(
            '{0}: Checking state of former build with PID:{1}'.format(
                ID, build_pid
            )
        )
        if psutil.pid_exists(build_pid):
            # TODO: send this information to kafka(cb-response)
            log.info(
                '{0}: Killing jobs associated with PID:{1} for rebuild'.format(
                    ID, build_pid
                )
            )
            os.kill(build_pid, signal.SIGTERM)

    if request['action'] == status_flags.package_changed:
        Command.run(
            ['git', '-C', Defaults.get_runner_project_dir(), 'pull']
        )
    run_script = dedent('''
        #!/bin/bash

        set -e

        function finish {{
            kill $(jobs -p) &>/dev/null
        }}

        {{
        trap finish EXIT
        cb-prepare --root {cb_root} --package {package_path}
    ''')
    for target in package_config.get('dists') or []:
        target_root = os.path.join(
            f'{package_root}@{target}'
        )
        run_script += dedent('''
            cb-run --root {target_root} &> {target_root}.log
        ''')
    run_script += dedent('''
        }} &>{package_root}.log &

        echo $! > {package_root}.pid
    ''')

    with open(package_run_script, 'w') as script:
        script.write(
            run_script.format(
                cb_root=cb_root,
                package_path=package_path,
                target_root=target_root,
                package_root=package_root
            )
        )

    Command.run(
        ['bash', package_run_script]
    )
