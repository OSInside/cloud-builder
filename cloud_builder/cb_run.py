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
       cb-run --root=<root_path>

options:
    --root=<root_path>
        Path to chroot to build the package. It's required
        that cb-prepare has created that chroot for cb-run
        to work
"""
import os
from docopt import docopt
from cloud_builder.version import __version__
from cloud_builder.exceptions import exception_handler
from cloud_builder.defaults import Defaults
from kiwi.privileges import Privileges
from kiwi.command import Command
from cloud_builder.cloud_logger import CBCloudLogger


@exception_handler
def main() -> None:
    args = docopt(
        __doc__,
        version='CB (run) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()

    package_name = args.get('--root').replace(
        Defaults.get_runner_package_root(), ''
    ).split('@')[0]

    log = CBCloudLogger('CBRun', package_name)

    build_log_file = os.path.join(
        args['--root'], '.build.log'
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
        find_call = Command.run(
            [
                'find', os.path.join(args['--root'], 'home', 'abuild'),
                '-name', '*.rpm'
            ]
        )
        if find_call.output:
            packages = find_call.output.strip().split(os.linesep)

    log.response(
        {
            'identity': log.get_id(),
            'message': 'Package build finished',
            'status': status,
            'package': package_name,
            'buildlog': build_log_file,
            'results': packages,
            'exitcode': exit_code
        }
    )
