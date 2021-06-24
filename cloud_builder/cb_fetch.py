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
usage: cb-fetch -h | --help
       cb-fetch --project=<github_project>
           [--update-interval=<time_sec>]
           [--single-shot]

options:
    --project=<github_project>
        git clone source URI to fetch project with
        packages managed to build in cloud builder

    --update-interval=<time_sec>
        Optional update interval for the project
        Default is 30sec

    --single-shot
        Optional single shot run. Only clone the repo
"""
import os
from docopt import docopt
from cloud_builder.version import __version__
from cloud_builder.logger import CBLogger
from cloud_builder.exceptions import exception_handler
from cloud_builder.defaults import Defaults
from cloud_builder.request import CBRequest
from cloud_builder.kafka import CBKafka
from kiwi.command import Command
from apscheduler.schedulers.background import BlockingScheduler
from kiwi.privileges import Privileges
from typing import (
    Dict, List
)

log = CBLogger.get_logger()


@exception_handler
def main() -> None:
    args = docopt(
        __doc__,
        version='CB (fetch) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()

    project_dir = Defaults.get_runner_project_dir()
    if not os.path.isdir(project_dir):
        Command.run(
            ['git', 'clone', args['--project'], project_dir]
        )
    if not args['--single-shot']:
        project_scheduler = BlockingScheduler()
        project_scheduler.add_job(
            lambda: update_project(),
            'interval', seconds=int(args['--update-interval'] or 30)
        )
        project_scheduler.start()


def update_project() -> None:
    Command.run(
        ['git', '-C', Defaults.get_runner_project_dir(), 'fetch', '--all']
    )
    git_changes = Command.run(
        [
            'git', '-C', Defaults.get_runner_project_dir(),
            'diff', '--name-only', 'origin/master'
        ]
    )
    changed_files = []
    changed_packages: Dict[str, List[str]] = {}
    if git_changes.output:
        changed_files = git_changes.output.strip().split(os.linesep)
    for changed_file in changed_files:
        if changed_file.startswith('projects'):
            package_dir = os.path.dirname(changed_file)
            if package_dir in changed_packages:
                changed_packages[package_dir].append(
                    os.path.basename(changed_file)
                )
            else:
                changed_packages[package_dir] = []
    Command.run(
        ['git', '-C', Defaults.get_runner_project_dir(), 'pull']
    )
    kafka = CBKafka(
        config_file=Defaults.get_kafka_config()
    )
    for package in sorted(changed_packages.keys()):
        log.info(f'Sending update request for package: {package!r}')
        request = CBRequest()
        request.set_package_source_change_request(package)
        kafka.send_request(request)
