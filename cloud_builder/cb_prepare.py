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
usage: cb-prepare -h | --help
       cb-prepare --root=<root_path> --package=<package_path> --profile=<dist> --request-id=<UUID>

options:
    --root=<root_path>
        Base path to create chroot(s) for later cb_run

    --package=<package_path>
        Path to the package

    --profile=<dist>
        Distribution profile name as set int the .kiwi
        package buildroot metadata file

    --request-id=<UUID>
        UUID for this prepare process
"""
import os
from docopt import docopt
from textwrap import dedent
from cloud_builder.version import __version__
from cloud_builder.cloud_logger import CBCloudLogger
from cloud_builder.broker import CBMessageBroker
from cloud_builder.response.response import CBResponse
from cloud_builder.exceptions import exception_handler
from cloud_builder.defaults import Defaults
from kiwi.command import Command
from kiwi.utils.sync import DataSync
from kiwi.privileges import Privileges
from kiwi.path import Path


@exception_handler
def main() -> None:
    """
    cb-prepare - creates a chroot tree suitable to build a
    package inside of it, also known as buildroot. The KIWI
    appliance builder is used to create the buildroot
    according to a metadata definition file from:

        Defaults.get_cloud_builder_kiwi_file_name()

    which needs to be present as part of the package sources.

    The build utility from the open build service is called
    from within a simple run.sh shell script that is written
    inside of the buildroot after KIWI has successfully created
    it. After this point, the buildroot is completely prepared
    and can be used to run the actual package build.
    """
    args = docopt(
        __doc__,
        version='CB (prepare) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()

    log = CBCloudLogger('CBPrepare', os.path.basename(args['--package']))

    status_flags = Defaults.get_status_flags()

    dist_profile = args['--profile']
    package_name = os.path.basename(args['--package'])

    target_root = os.path.normpath(
        os.sep.join(
            [args["--root"], f'{package_name}@{dist_profile}']
        )
    )

    # Solve buildroot packages and create solver json
    solver_json_file = f'{target_root}.solver.json'
    log.info(
        'Solving buildroot package list for {0}. For details see: {1}'.format(
            target_root, solver_json_file
        )
    )
    kiwi_solve = Command.run(
        [
            Path.which(
                'kiwi-ng', alternative_lookup_paths=['/usr/local/bin']
            ),
            '--profile', dist_profile,
            'image', 'info',
            '--description', args['--package'],
            '--resolve-package-list'
        ], raise_on_error=False
    )
    exit_code = kiwi_solve.returncode
    if kiwi_solve.output:
        with open(solver_json_file, 'w') as solve_log:
            process_line = False
            for line in kiwi_solve.output.split(os.linesep):
                if line.startswith('{'):
                    process_line = True
                if process_line:
                    solve_log.write(line)
                    solve_log.write(os.linesep)

    # Install buildroot and create prepare log
    prepare_log_file = f'{target_root}.prepare.log'
    with open(prepare_log_file, 'w'):
        pass
    if kiwi_solve.returncode == 0:
        log.info(
            'Creating buildroot {0}. For details see: {1}'.format(
                target_root, prepare_log_file
            )
        )
        kiwi_run = Command.run(
            [
                Path.which(
                    'kiwi-ng', alternative_lookup_paths=['/usr/local/bin']
                ),
                '--logfile', prepare_log_file,
                '--profile', dist_profile,
                'system', 'prepare',
                '--description', args['--package'],
                '--allow-existing-root',
                '--root', target_root
            ], raise_on_error=False
        )
        exit_code = kiwi_run.returncode

    # Sync package sources and build script into buildroot
    if exit_code != 0:
        status = status_flags.buildroot_setup_failed
        message = 'Failed in kiwi stage, see logfile for details'
    else:
        try:
            data = DataSync(
                f'{args["--package"]}/',
                f'{target_root}/{package_name}/'
            )
            data.sync_data(
                options=['-a', '-x']
            )
            run_script = dedent('''
                #!/bin/bash

                set -e

                function finish {{
                    for path in /proc /dev;do
                        mountpoint -q "$path" && umount "$path"
                    done
                }}

                trap finish EXIT

                mount -t proc proc /proc
                mount -t devtmpfs devtmpfs /dev

                pushd {0}
                build --no-init --root /
            ''')
            with open(f'{target_root}/run.sh', 'w') as script:
                script.write(
                    run_script.format(package_name)
                )
            status = status_flags.buildroot_setup_succeeded
            message = 'Buildroot ready for package build'
        except Exception as issue:
            status = status_flags.buildroot_setup_failed
            exit_code = 1
            message = format(issue)

    # Send result response to the message broker
    response = CBResponse(args['--request-id'], log.get_id())
    response.set_package_buildroot_response(
        message=message,
        response_code=status,
        package=package_name,
        log_file=prepare_log_file,
        solver_file=solver_json_file,
        build_root=target_root,
        exit_code=exit_code
    )
    broker = CBMessageBroker.new(
        'kafka', config_file=Defaults.get_kafka_config()
    )
    log.response(response, broker)
