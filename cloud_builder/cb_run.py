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
from cloud_builder.identity import CBIdentity
from cloud_builder.defaults import Defaults
from kiwi.privileges import Privileges
from kiwi.command import Command
from cloud_builder.logger import CBLogger

log = CBLogger.get_logger(
    logfile=Defaults.get_cb_logfile()
)

ID = CBIdentity.get_id('CBKafka')


@exception_handler
def main() -> None:
    args = docopt(
        __doc__,
        version='CB (run) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()

    build_run = [
        'chroot', args['--root'], 'bash', '/run.sh'
    ]
    return_value = os.system(
        ' '.join(build_run)
    )
    exit_code = return_value >> 8
    build_log_file = ''
    packages = []

    if exit_code != 0:
        log.error('{ID}: Build Failed')
    else:
        build_log_file = os.path.join(args['--root'], '.build.log')
        find_call = Command.run(
            [
                'find', os.path.join(args['--root'], 'home', 'abuild'),
                '-name', '*.rpm'
            ]
        )
        if find_call.output:
            packages = find_call.output.strip().split(os.linesep)

    # TODO: send this information to kafka(cb-response)
    log.info(f'{ID}: {build_log_file}')
    log.info(f'{ID}: {packages}')
    log.info(f'{ID}: {exit_code}')
