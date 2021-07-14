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
       cb-ctl --build=<package> --project-path=<path> --arch=<name> --dist=<name>
       cb-ctl --info=<package>
           [--timeout=<time_sec>]
       cb-ctl --watch
           [--filer-request-id=<uuid>]
           [--timeout=<time_sec>]

options:
    --build=<package>
        Create a request to build the given package.
        The provided argument is appended to the
        project-path and forms the directory path
        to the package in the git repository

        projects/
        └── <project-path>/
                    └── <package>/...

        Please note, the root directory is by convention
        a fixed name set to 'projects'

    --project-path=<path>
        Project path that points to the package in the git.
        See the above structure example

    --arch=<name>
        Target architecture name

    --dist=<name>
        Target distribution name

    --info=<package>
        Provide status information for package

    --watch
        Watch response messages of the cloud builder system

    --filer-request-id=<uuid>
        Filter messages by given request UUID

    --timeout=<time_sec>
        Wait time_sec seconds of inactivity on the message
        broker before return. Default: 30sec
"""
import os
from docopt import docopt
from typing import (
    Any, Dict, Optional, Callable
)

from cloud_builder.version import __version__
from cloud_builder.defaults import Defaults
from cloud_builder.broker import CBMessageBroker
from cloud_builder.package_request.package_request import CBPackageRequest
from cloud_builder.utils.display import CBDisplay
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

    broker = CBMessageBroker.new(
        'kafka', config_file=Defaults.get_kafka_config()
    )

    if args['--build']:
        build_package(
            broker,
            args['--build'],
            args['--project-path'],
            args['--arch'],
            args['--dist']
        )
    elif args['--info']:
        get_package_info(
            broker,
            args['--info'],
            args['--timeout']
        )
    elif args['--watch']:
        timeout = int(args['--timeout'] or 30)
        if args['--filer-request-id']:
            response_reader(broker, timeout, response_filter_request_id)
        else:
            response_reader(broker, timeout, response_filter_none)


def build_package(
    broker: Any, package: str, project_path: str, arch: str, dist: str
) -> None:
    package_request = CBPackageRequest()
    package_request.set_package_build_request(
        os.path.join(
            'projects', project_path, package,
        ), arch, dist,
        Defaults.get_status_flags().package_update_request
    )
    broker.send_package_request(package_request)
    CBDisplay.print_yaml(package_request.get_data())
    broker.close()


def get_package_info(
    broker: Any, package: str, timeout_sec: int
) -> None:
    # TODO
    pass


def watch_response_queue(
    broker: Any, request_id: Optional[str], timeout_sec: int
) -> None:
    try:
        while(True):
            message = None
            for message in broker.read(
                topic=Defaults.get_response_queue_name(),
                group=f'cb-ctl:watch:{os.getpid()}',
                timeout_ms=timeout_sec * 1000
            ):
                response = broker.validate_package_response(message.value)
                if response:
                    broker.acknowledge()
                    if response['request_id'] == request_id:
                        CBDisplay.print_yaml(response)
            if not message:
                break
    finally:
        broker.close()


def response_filter_request_id(response: Dict) -> None:
    CBDisplay.print_yaml(response)


def response_filter_none(response: Dict) -> None:
    CBDisplay.print_yaml(response)


def response_reader(
    broker: Any, timeout_sec: int, func: Callable
) -> None:
    """
    Read from the cloud builder response queue

    :param CBMessageBroker broker: broker instance
    :param int timeout_sec:
        Wait time_sec seconds of inactivity on the message
        broker before return.
    :param Callable func:
        Call method for response
    """
    try:
        while(True):
            message = None
            for message in broker.read(
                topic=Defaults.get_response_queue_name(),
                group=f'cb-ctl:{os.getpid()}',
                timeout_ms=timeout_sec * 1000
            ):
                response = broker.validate_package_response(
                    message.value
                )
                if response:
                    broker.acknowledge()
                    func(response)
            if not message:
                break
    finally:
        broker.close()
