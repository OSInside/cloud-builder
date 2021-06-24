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

options:
    --update-interval=<time_sec>
        Optional update interval for the lookup
        of the kafka cb_request topic
        Default is 30sec
"""
import os
from docopt import docopt
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


@exception_handler
def main() -> None:
    args = docopt(
        __doc__,
        version='CB (scheduler) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()

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
    # FIXME: only for testing
    fake_request = [
        {
            'schema_version': 0.1,
            'package': 'projects/MS/xclock',
            'action': 'package_changed'
        }
    ]
    # for request in kafka.read_request():
    for request in fake_request:
        package_path = os.path.join(
            Defaults.get_runner_project_dir(), format(request['package'])
        )
        Command.run(
            ['git', '-C', Defaults.get_runner_project_dir(), 'pull']
        )
        package_config = Defaults.get_package_config(
            package_path
        )
        cb_prepare = [
            Path.which(
                'cb-prepare', alternative_lookup_paths=['/usr/local/bin']
            ), '--root', '/var/tmp', '--package', package_path
        ]
        os.system(
            ' '.join(cb_prepare)
        )
        for target in package_config.get('dists') or []:
            target_root = os.path.join(
                '/var', 'tmp', f'{package_config["name"]}@{target}'
            )
            cb_run = [
                Path.which(
                    'cb-run', alternative_lookup_paths=['/usr/local/bin']
                ), '--root', target_root
            ]
            os.system(
                ' '.join(cb_run)
            )
