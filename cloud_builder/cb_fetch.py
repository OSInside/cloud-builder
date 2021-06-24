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
usage: cb_fetch -h | --help
       cb_fetch --project=<github_project>
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
from kiwi.command import Command
from apscheduler.schedulers.background import BlockingScheduler

log = CBLogger.get_logger()


@exception_handler
def main() -> None:
    args = docopt(
        __doc__,
        version='CB (fetch) version ' + __version__,
        options_first=True
    )
    project_dir = Defaults.get_runner_project_dir()
    if not os.path.isdir(project_dir):
        Command.run(
            ['git', 'clone', args['--project'], project_dir]
        )
    if not args['--single-shot']:
        project_scheduler = BlockingScheduler()
        project_scheduler.add_job(
            lambda: update_project(),
            'interval', seconds=args['--update-interval'] or 30
        )
        project_scheduler.start()


def update_project() -> None:
    git_update = Command.run(
        ['git', '-C', Defaults.get_runner_project_dir(), 'pull']
    )
    log.info(git_update.output)
