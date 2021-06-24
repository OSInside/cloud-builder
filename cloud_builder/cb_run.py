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
usage: cb_run -h | --help
       cb_run --root=<root_path> --package=<package_path>

options:
    --root=<root_path>
        Path to chroot to build the package in

    --package=<package_path>
        Path to the package
"""
from docopt import docopt
from cloud_builder.version import __version__
from cloud_builder.logger import CBLogger
from cloud_builder.exceptions import exception_handler
from kiwi.privileges import Privileges

log = CBLogger.get_logger()


@exception_handler
def main() -> None:
    docopt(
        __doc__,
        version='CB (run) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()
