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
usage: cb-ctl -h | --help
       cb-ctl --build=<package>
       cb-ctl --info=<package>
           [--timeout=<time_sec>]
       cb-ctl --watch --request-id=<uuid>
           [--timeout=<time_sec>]

options:
    --timeout=<time_sec>
        Wait time_sec seconds of inactivity on the message
        broker before return. Default: 30sec
"""
from docopt import docopt
from cloud_builder.version import __version__
from kiwi.privileges import Privileges
# from cloud_builder.defaults import Defaults
# from cloud_builder.package_request.package_request import CBPackageRequest
from cloud_builder.exceptions import exception_handler


@exception_handler
def main() -> None:
    """
    cb-ctl - cloud builder control utility
    """
    args = docopt(
        __doc__,
        version='CB (ctl) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()

    if args['--build']:
        build_package(args['--build'])
    elif args['--info']:
        get_package_info(args['--info'], args['--timeout'])
    elif args['--watch']:
        get_response_for_request(args['--request-id'], args['--timeout'])


def build_package(packge: str) -> None:
    # broker = CBMessageBroker.new(
    #     'kafka', config_file=Defaults.get_kafka_config()
    # )
    # package_request = CBPackageRequest()
    pass


def get_package_info(package: str, timeout_sec: int) -> None:
    pass


def get_response_for_request(request_id: str, timeout_sec: int) -> None:
    pass
