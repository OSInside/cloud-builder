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
usage: cb-info -h | --help
       cb-info
           [--update-interval=<time_sec>]

options:
    --update-interval=<time_sec>
        Optional update interval for the lookup
        Default is 30sec

"""
from docopt import docopt
from cloud_builder.version import __version__
from cloud_builder.exceptions import exception_handler
from kiwi.privileges import Privileges


@exception_handler
def main() -> None:
    """
    cb-info - lookup package information. The package
    builds on a runner contains a number of files like
    the following example:

    /var/tmp/CB/
           ├── package.pid
           ├── package.sh
           ├── package@DIST.ARCH
           ├── package@DIST.ARCH.build.log
           └── package@DIST.ARCH.prepare.log

    The local file information is used to construct
    a response record with information about the
    package build:

    * package status, running/succeeded/failed
    * per arch:
      * package prepare log contents
      * package build log contents
      * timestamp of build log
      * scp command to fetch binaries
    """
    args = docopt(
        __doc__,
        version='CB (info) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()
    print(args)


def lookup(package: str, request_id: str):
    pass
