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
usage: cb-run -h | --help
       cb-run --root=<root_path> --request-id=<UUID>
           [(--repo-server=<name> --repo-path=<path> --ssh-user=<user> --ssh-pkey=<ssh_pkey_file>)]
           [--local]
           [--clean]

options:
    --root=<root_path>
        Path to chroot to build the package. It's required
        that cb-prepare has created that chroot for cb-run
        to work

    --request-id=<UUID>
        UUID for this build process

    --repo-path=<path>
        Path to place build results on the repo server

    --repo-server=<name>
        Name or IP of collector repo server

    --ssh-pkey=<ssh_pkey_file>
        Path to ssh private key file to access repo server

    --ssh-user=<user>
        User name to access repo server

    --clean
        Delete chroot system after build and keep
        only results if there are any

    --local
        Operate locally:
        * do not send results to the message broker
"""
import os
import sys
from docopt import docopt
from typing import List

from cloud_builder.version import __version__
from cloud_builder.exceptions import exception_handler
from cloud_builder.broker import CBMessageBroker
from cloud_builder.defaults import Defaults
from kiwi.privileges import Privileges
from kiwi.command import Command
from kiwi.path import Path
from cloud_builder.cloud_logger import CBCloudLogger
from cloud_builder.response.response import CBResponse
from cloud_builder.utils.repository import CBRepository


@exception_handler
def main() -> None:
    """
    cb-run - builds packages by calling the run.sh script
    which must be present in the given root_path. cb-run
    is usually called after cb-prepare which creates an
    environment to satisfy the cb-run requirements

    The called run.sh script is expected to run a program
    that builds packages and stores them below the path
    returned by Defaults.get_runner_result_paths()

    At the end of cb-run an information record will be send
    to preserve the result information for later use
    """
    args = docopt(
        __doc__,
        version='CB (run) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()

    package_name = args.get('--root').replace(
        Defaults.get_runner_root(), ''
    ).split('@')[0].strip(os.sep)

    log = CBCloudLogger('CBRun', package_name)
    log.set_logfile()

    # created by run.sh script written in cb_prepare and called here
    prepare_log_file = ''.join(
        [args['--root'].rstrip(os.sep), '.prepare.log']
    )
    # created by run.sh script written in cb_prepare and called here
    build_log_file = ''.join(
        [args['--root'].rstrip(os.sep), '.build.log']
    )
    # created by kiwi resolve-package-list called in cb_prepare
    solver_json_file = ''.join(
        [args['--root'].rstrip(os.sep), '.solver.json']
    )
    build_result_file = ''.join(
        [args['--root'].rstrip(os.sep), '.result.yml']
    )
    log.info(
        f'Starting package build. For details see: {build_log_file}'
    )
    build_run = [
        'chroot', args['--root'], 'bash', '/run.sh'
    ]
    return_value = os.system(
        ' '.join(build_run)
    )
    exit_code = return_value >> 8
    status_flags = Defaults.get_status_flags()
    packages = []

    if exit_code != 0:
        status = status_flags.package_build_failed
    else:
        status = status_flags.package_build_succeeded

        # create binaries directory to hold build results
        package_build_binary_dir = f'{args["--root"]}.binaries'
        package_build_target_dir = package_build_binary_dir

        if args['--repo-path']:
            # if the repo path is provided create this dir structure
            # to simplify the later sync process to the repo server
            package_build_target_dir = os.sep.join(
                [package_build_target_dir, args['--repo-path']]
            )

        Path.wipe(package_build_target_dir)
        Path.create(package_build_target_dir)

        package_result_paths = [
            os.path.join(
                args['--root'], path
            ) for path in Defaults.get_runner_result_paths()
        ]
        package_lookup: List[str] = []
        for package_format in Defaults.get_package_formats():
            if not package_lookup:
                package_lookup.extend(['-name', package_format])
            else:
                package_lookup.extend(['-or', '-name', package_format])
        find_call = Command.run(
            ['find'] + package_result_paths + ['-type', 'f'] + package_lookup,
            raise_on_error=False
        )
        if find_call.output:
            for package in find_call.output.strip().split(os.linesep):
                repo_meta = CBRepository(package).get_repo_meta(
                    base_repo_path=package_build_target_dir
                )
                os.rename(package, repo_meta.repo_file)
        else:
            exit_code = 1
            status = status_flags.package_build_failed_no_binaries
            log.error(status)

        if args['--clean']:
            # delete build root and re-create empty
            Path.wipe(args['--root'])
            Path.create(args['--root'])

        # Move binary contents to root tree
        target_binary_dir = os.sep.join(
            [args['--root'], os.path.basename(package_build_binary_dir)]
        )
        os.rename(
            package_build_binary_dir, target_binary_dir
        )
        # Create packages list
        for root, dirs, files in os.walk(target_binary_dir):
            for entry in files:
                packages.append(os.path.join(root, entry))
        log.info(format(packages))

        # Sync target_binary_dir to repo server
        if args['--repo-server']:
            update_repo_indicator = os.path.join(
                target_binary_dir, args['--repo-path'], '.updaterepo'
            )
            # Write an update repo indicator to tell the collector
            # to rebuild the repo metadata
            Command.run(
                ['touch', update_repo_indicator]
            )
            sync_call = Command.run(
                [
                    'rsync', '-av', '-e', 'ssh -i {0} -o {1}'.format(
                        args['--ssh-pkey'],
                        'StrictHostKeyChecking=accept-new'
                    ), f'{target_binary_dir}/', '{0}@{1}:{2}'.format(
                        args['--ssh-user'], args['--repo-server'],
                        Defaults.get_repo_root()
                    )
                ], raise_on_error=False
            )
            if sync_call.output:
                log.info(sync_call.output)
            if sync_call.error:
                exit_code = 1
                status = status_flags.package_binaries_sync_failed
                log.error(sync_call.error)

    if not args['--local']:
        response = CBResponse(args['--request-id'], log.get_id())
        response.set_package_build_response(
            message='Package build finished',
            response_code=status,
            package=package_name,
            prepare_log_file=prepare_log_file,
            log_file=build_log_file,
            solver_file=solver_json_file,
            binary_packages=packages,
            exit_code=exit_code
        )
        broker = CBMessageBroker.new(
            'kafka', config_file=Defaults.get_broker_config()
        )
        log.response(response, broker, build_result_file)

    sys.exit(exit_code)
