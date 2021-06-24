# Copyright (c) 2021 Marcus Schäfer.  All rights reserved.
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
from cloud_builder.kafka import CBKafka
from kiwi.command import Command
from apscheduler.schedulers.background import BlockingScheduler

log = CBLogger.get_logger()


@exception_handler
def main() -> None:
    args = docopt(
        __doc__,
        version='CB (scheduler) version ' + __version__,
        options_first=True
    )
    project_scheduler = BlockingScheduler()
    project_scheduler.add_job(
        lambda: handle_requests(),
        'interval', seconds=int(args['--update-interval'] or 30)
    )
    project_scheduler.start()


def handle_requests() -> None:
    kafka = CBKafka(
        config_file=Defaults.get_kafka_config()
    )
    for request in kafka.read_request():
        package_path = os.path.join(
            Defaults.get_runner_project_dir(), request['package']
        )
        Command.run(
            ['git', '-C', Defaults.get_runner_project_dir(), 'pull']
        )
        package_config = Defaults.get_package_config(
            package_path
        )
        Command.run(
            [
                'cb-prepare', '--root', '/var/tmp',
                '--package', package_path
            ]
        )
        for target in package_config.get('dists') or []:
            target_root = os.path.join(
                '/var', 'tmp', f'{package_config["name"]}@{target}'
            )
            Command.run(
                ['cb-run', '--root', target_root]
            )
