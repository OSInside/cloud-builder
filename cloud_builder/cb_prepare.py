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
       cb-prepare --root=<root_path> --package=<package_path>
           [--config=<file>]

options:
    --root=<root_path>
        Base path to create chroot(s) for later cb_run

    --package=<package_path>
        Path to the package

    --config=<file>
        Package config file. Contains specifications how to
        build the package and for which targets. By default
        cloud_builder.yml from the package directory is used
"""
import os
from docopt import docopt
from textwrap import dedent
from cloud_builder.version import __version__
from cloud_builder.logger import CBLogger
from cloud_builder.exceptions import exception_handler
from cloud_builder.defaults import Defaults
from kiwi.utils.sync import DataSync
from kiwi.privileges import Privileges
from kiwi.path import Path
from typing import Dict

log = CBLogger.get_logger()


@exception_handler
def main() -> None:
    args = docopt(
        __doc__,
        version='CB (prepare) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()

    package_config = Defaults.get_package_config(
        args['--package'], args['--config']
    )
    target_root_dict: Dict = {
        'target_roots': []
    }
    for target in package_config.get('dists') or []:
        target_root = os.path.normpath(
            os.sep.join(
                [args["--root"], f'{package_config["name"]}@{target}']
            )
        )
        kiwi_run = [
            Path.which(
                'kiwi-ng', alternative_lookup_paths=['/usr/local/bin']
            ), '--logfile', f'{target_root}.prepare.log', '--profile', target,
            'system', 'prepare', '--description', args['--package'],
            '--allow-existing-root', '--root', target_root
        ]
        return_value = os.system(
            ' '.join(kiwi_run)
        )
        exit_code = return_value >> 8
        if exit_code != 0:
            log.error(f'Preparation of {target_root} failed')
            # TODO: send this information to kafka(cb-response)
            continue

        data = DataSync(
            f'{args["--package"]}/',
            f'{target_root}/{package_config["name"]}/'
        )
        data.sync_data(
            options=['-a', '-x']
        )
        target_root_dict['target_roots'].append(
            target_root
        )
        run_script = dedent('''
            #!/bin/bash

            set -e

            function increment_release {{
                local release=1
                test -e release && release=$(( $(cat release) + 1 ))
                echo "$release" > release
                echo "$release"
            }}

            function finish {{
                for path in /proc /dev;do
                    mountpoint -q "$path" && umount "$path"
                done
            }}

            trap finish EXIT

            mount -t proc proc /proc
            mount -t devtmpfs devtmpfs /dev

            pushd {0}
            build --no-init \\
                --release $(increment_release) --root /
        ''')
        with open(f'{target_root}/run.sh', 'w') as script:
            script.write(
                run_script.format(package_config['name'])
            )
