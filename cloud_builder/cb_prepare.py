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
usage: cb_prepare -h | --help
       cb_prepare --root=<root_path> --package=<package_path>
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
import yaml
import sys
from docopt import docopt
from cloud_builder.version import __version__
from cloud_builder.logger import CBLogger
from cloud_builder.exceptions import exception_handler
from kiwi.utils.sync import DataSync

log = CBLogger.get_logger()


@exception_handler
def main() -> None:
    args = docopt(
        __doc__,
        version='CB (prepare) version ' + __version__,
        options_first=True
    )
    config_file = \
        args['--config'] or os.path.join(args['--package'], 'cloud_builder.yml')
    with open(config_file, 'r') as config:
        package_config = yaml.safe_load(config) or {}

    target_root_dict = {
        'target_roots': []
    }
    for target in package_config.get('dists') or []:
        target_root = os.path.normpath(
            os.sep.join(
                [args["--root"], f'{package_config["name"]}@{target}']
            )
        )
        kiwi_run = [
            'kiwi-ng', '--profile', target,
            'system', 'prepare', '--description', args['--package'],
            '--allow-existing-root', '--root', target_root
        ]
        os.system(
            ' '.join(kiwi_run)
        )
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
    yaml.safe_dump(
        target_root_dict, sys.stdout, allow_unicode=True
    )
