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
from docopt import docopt
from textwrap import dedent
from cloud_builder.version import __version__
from cloud_builder.logger import CBLogger
from cloud_builder.exceptions import exception_handler
from cloud_builder.defaults import Defaults
# from cloud_builder.kafka import CBKafka
from kiwi.command import Command
from kiwi.privileges import Privileges
from kiwi.path import Path
from apscheduler.schedulers.background import BlockingScheduler

log = CBLogger.get_logger()

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

    project_scheduler = BlockingScheduler()
    project_scheduler.add_job(
        lambda: handle_requests(),
        'interval', seconds=int(args['--update-interval'] or 30)
    )
    project_scheduler.start()


def handle_requests() -> None:
    # kafka = CBKafka(
    #     config_file=Defaults.get_kafka_config()
    # )
    status_flags = Defaults.get_status_flags()

    # FIXME: only for testing
    from cloud_builder.kafka import kafka_read_type
    kafka_request_topic = kafka_read_type(
        consumer=None,
        message_list=[
            {
                'schema_version': 0.1,
                'package': 'projects/MS/xclock',
                'action': status_flags.package_changed
            }
        ]
    )

    # kafka_request_topic = kafka.read_request()

    global running_builds
    global running_limit
    # TODO: lookup current running limit

    if running_builds <= running_limit:
        # kafka.acknowledge(kafka_request_topic.consumer)
        pass
    else:
        # Do not acknowledge if running_limit is exceeded.
        # The request will stay in the queue and gets
        # handled by another runner or this one if the
        # limit is no longer exceeded
        # TODO: send this information to kafka(cb-response)
        return

    for request in kafka_request_topic.message_list:
        package_path = os.path.join(
            Defaults.get_runner_project_dir(), format(request['package'])
        )
        package_config = Defaults.get_package_config(
            package_path
        )
        cb_root = '/var/tmp/CB'
        Path.create(cb_root)
        package_root = os.path.join(
            cb_root, f'{package_config["name"]}'
        )
        package_run_script = f'{package_root}.sh'

        # TODO: check if package is currently building,
        # if yes, delete and restart
        # package_run_pid = f'{package_root}.pid'

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
