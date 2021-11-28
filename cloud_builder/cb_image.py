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
usage: cb-image -h | --help
       cb-image --description=<image_description_path> --target-dir=<target_path> --bundle-id=<ID> --request-id=<UUID>
           [(--repo-server=<name> --repo-path=<path> --ssh-user=<user> --ssh-pkey=<ssh_pkey_file>)]
           [--local]
           [--profile=<name>...]
           [-- <kiwi_custom_build_command_args>...]

options:
    --description=<image_description_path>
        Path to KIWI image description

    --target-dir=<target_path>
        Path to create image result package

    --bundle-id=<ID>
        Identifier added to the build result file names

    --profile=<name>...
        List of optional profile names to use for building

    --request-id=<UUID>
        UUID for this image build process

    --repo-path=<path>
        Path to place build results on the repo server

    --repo-server=<name>
        Name or IP of collector repo server

    --ssh-pkey=<ssh_pkey_file>
        Path to ssh private key file to access repo server

    --ssh-user=<user>
        User name to access repo server

    --local
        Operate locally:
        * do not send results to the message broker
        * do not create dependency graph
        * run operations in debug mode

    -- <kiwi_custom_build_command_args>...
        List of additional kiwi build command arguments
        See 'kiwi-ng system build --help' for details
"""
import os
import sys
import json
import glob
from docopt import docopt
from tempfile import TemporaryDirectory
from kiwi.command import Command
from kiwi.path import Path

from cloud_builder.version import __version__
from cloud_builder.cloud_logger import CBCloudLogger
from cloud_builder.broker import CBMessageBroker
from cloud_builder.response.response import CBResponse
from cloud_builder.exceptions import exception_handler
from cloud_builder.cb_prepare import resolve_build_dependencies
from cloud_builder.utils.repository import CBRepository
from cloud_builder.defaults import Defaults

from kiwi.privileges import Privileges


@exception_handler
def main() -> None:
    """
    cb-image - builds an image using KIWI.
    Inside of the image_description_path a KIWI image
    description is expected. The process of building the
    image is two fold:

    * Build the image
    * Bundle image result file(s) into an rpm package

    The created image root tree will be deleted after
    the image build. The reason for this is that building
    an image should always start from a clean state to
    guarantee the root tree integrity with respect to the
    used package repositories
    """
    args = docopt(
        __doc__,
        version='CB (image) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()

    image_name = os.path.basename(args['--description'])

    log = CBCloudLogger('CBImage', image_name)
    log.set_logfile()

    status_flags = Defaults.get_status_flags()

    profiles = []
    for profile in args['--profile']:
        profiles.extend(['--profile', profile])

    image_build_target_dir = TemporaryDirectory(
        dir='/var/tmp', prefix='kiwi_image_'
    )

    custom_build_options = args['<kiwi_custom_build_command_args>']

    target_dir = args['--target-dir']
    build_log_file = f'{target_dir}.build.log'
    build_result_file = f'{target_dir}.result.yml'
    solver_json_file = f'{target_dir}.solver.json'

    # Solve image packages and create solver json
    if not args['--local']:
        log.info(
            'Solving image package list for {0}. Details in: {1}'.format(
                args['--description'], solver_json_file
            )
        )
        solver_result = resolve_build_dependencies(
            source_path=args['--description'],
            profile_list=args['--profile'],
            log_file=build_log_file,
            resolve_for_image_source=True
        )
        with open(solver_json_file, 'w') as solve_result:
            solve_result.write(
                json.dumps(
                    solver_result['solver_data'], sort_keys=True, indent=4
                )
            )

    # Build and package image
    kiwi_binary = Defaults.get_kiwi()
    kiwi_build = [kiwi_binary]
    if not args['--local']:
        kiwi_build.extend(
            ['--logfile', build_log_file]
        )
    else:
        kiwi_build.append('--debug')
    if profiles:
        kiwi_build.extend(profiles)
    kiwi_build.extend(
        [
            'system', 'build',
            '--description', args['--description'],
            '--allow-existing-root',
            '--target-dir', image_build_target_dir.name
        ] + custom_build_options
    )
    log.info(
        'Building image {0}. Details in: {1}'.format(
            args['--description'], build_log_file
        )
    )
    exit_code = os.WEXITSTATUS(
        os.system(' '.join(kiwi_build))
    )
    if exit_code == 0:
        log.info(
            'Bundle image {0}. Details in: {1}'.format(
                target_dir, build_log_file
            )
        )
        kiwi_bundle = [kiwi_binary]
        if not args['--local']:
            kiwi_bundle.extend(
                ['--logfile', build_log_file]
            )
        else:
            kiwi_bundle.append('--debug')
        kiwi_bundle.extend(
            [
                'result', 'bundle',
                '--target-dir', image_build_target_dir.name,
                '--id', args['--bundle-id'],
                '--bundle-dir', target_dir,
                '--package-as-rpm'
            ]
        )
        exit_code = os.WEXITSTATUS(
            os.system(' '.join(kiwi_bundle))
        )

    packages = []

    if exit_code != 0:
        status = status_flags.image_build_failed
        message = 'Failed, see logfile for details'
    else:
        status = status_flags.image_build_succeeded
        message = 'Image build bundled as RPM package'

        # create binaries directory to hold build results
        package_build_binary_dir = f'{target_dir}.binaries'
        package_build_target_dir = package_build_binary_dir

        if args['--repo-path']:
            # if the repo path is provided create this dir structure
            # to simplify the later sync process to the repo server
            package_build_target_dir = os.sep.join(
                [package_build_target_dir, args['--repo-path']]
            )

        Path.wipe(package_build_target_dir)
        Path.create(package_build_target_dir)

        for package in glob.iglob(f'{target_dir}/*'):
            repo_meta = CBRepository(package).get_repo_meta(
                base_repo_path=package_build_target_dir
            )
            os.rename(package, repo_meta.repo_file)

        Path.wipe(target_dir)
        os.rename(
            package_build_binary_dir, target_dir
        )
        # Create packages list
        for root, dirs, files in os.walk(target_dir):
            for entry in files:
                packages.append(os.path.join(root, entry))
        log.info(format(packages))

        # Sync target_binary_dir to repo server
        if args['--repo-server']:
            update_repo_indicator = os.path.join(
                target_dir, args['--repo-path'], '.updaterepo'
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
                    ), f'{target_dir}/', '{0}@{1}:{2}'.format(
                        args['--ssh-user'], args['--repo-server'],
                        Defaults.get_repo_root()
                    )
                ], raise_on_error=False
            )
            if sync_call.output:
                log.info(sync_call.output)
            if sync_call.returncode != 0:
                exit_code = 1
                status = status_flags.package_binaries_sync_failed
                log.error(sync_call.error)

    # Send result response to the message broker
    if not args['--local']:
        response = CBResponse(args['--request-id'], log.get_id())
        response.set_image_build_response(
            message=message,
            response_code=status,
            image=image_name,
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
