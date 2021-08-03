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
from cloud_builder.cloud_logger import CBCloudLogger
from cloud_builder.identity import CBIdentity
from cloud_builder.exceptions import exception_handler
from cloud_builder.defaults import Defaults
from cloud_builder.package_metadata.package_metadata import CBPackageMetaData
from cloud_builder.package_request.package_request import CBPackageRequest
from cloud_builder.broker import CBMessageBroker
from cloud_builder.response.response import CBResponse
from kiwi.command import Command
from apscheduler.schedulers.background import BlockingScheduler
from kiwi.privileges import Privileges
from typing import (
    Dict, List
)


@exception_handler
def main() -> None:
    """
    cb-fetch - fetches a git repository and manages content
    changes on a configurable schedule. In case of a change
    a rebuild request is send to the message broker

    The tree structure in the git repository has to respect
    a predefined layout like in the following example:

    projects
    ├── ...
    ├── PROJECT_A
    │   └── SUB_PROJECT
    │       └── ...
    └── PROJECT_B
        └── PACKAGE
            ├── _Defaults.get_cloud_builder_metadata_file_name()_
            ├── _Defaults.get_cloud_builder_kiwi_file_name()_
            ├── PACKAGE.changes
            ├── PACKAGE.spec
            └── PACKAGE.tar.xz
    """
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
        update_project()

        project_scheduler = BlockingScheduler()
        project_scheduler.add_job(
            lambda: update_project(),
            'interval', seconds=int(args['--update-interval'] or 30)
        )
        project_scheduler.start()


def update_project() -> None:
    """
    Callback method registered with the BlockingScheduler
    """
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
                changed_packages[package_dir] = [
                    os.path.basename(changed_file)
                ]
    Command.run(
        ['git', '-C', Defaults.get_runner_project_dir(), 'pull']
    )
    broker = CBMessageBroker.new(
        'kafka', config_file=Defaults.get_broker_config()
    )
    for package_source_path in sorted(changed_packages.keys()):
        log = CBCloudLogger('CBFetch', os.path.basename(package_source_path))
        package_config = CBPackageMetaData.get_package_config(
            os.path.join(
                Defaults.get_runner_project_dir(), package_source_path
            ), log, CBIdentity.get_request_id()
        )
        if package_config:
            status_flags = Defaults.get_status_flags()
            request_action = status_flags.package_source_rebuild
            buildroot_config = Defaults.get_cloud_builder_kiwi_file_name()
            if buildroot_config in changed_packages[package_source_path]:
                # buildroot setup is part of changes list. This
                # triggers a new build of the package buildroot
                request_action = status_flags.package_source_rebuild_clean
            for target in package_config.get('distributions') or []:
                package_request = CBPackageRequest()
                package_request.set_package_build_request(
                    package_source_path, target['arch'], target['dist'],
                    target['runner_group'], request_action
                )
                broker.send_package_request(package_request)
                request = package_request.get_data()
                response = CBResponse(
                    request['request_id'], log.get_id()
                )
                response.set_package_update_request_response(
                    message='Package update request scheduled',
                    response_code=request_action,
                    package=request['package'],
                    arch=request['arch'],
                    dist=request['dist']
                )
                log.response(response, broker)
