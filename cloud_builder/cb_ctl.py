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
       cb-ctl --build-dependencies=<package> --arch=<name> --dist=<name>
           [--timeout=<time_sec>]
       cb-ctl --watch
           [--filter-request-id=<uuid>]
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

    --build-dependencies=<package>
        Provide build root dependency information

    --watch
        Watch response messages of the cloud builder system

    --filter-request-id=<uuid>
        Filter messages by given request UUID

    --timeout=<time_sec>
        Wait time_sec seconds of inactivity on the message
        broker before return. Default: 30sec
"""
import os
from docopt import docopt
from datetime import datetime
from typing import (
    Any, Dict, Callable
)

from cloud_builder.version import __version__
from cloud_builder.defaults import Defaults
from cloud_builder.broker import CBMessageBroker
from cloud_builder.package_request.package_request import CBPackageRequest
from cloud_builder.info_request.info_request import CBInfoRequest
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
    elif args['--build-dependencies']:
        get_build_dependencies(
            broker,
            args['--build-dependencies'],
            args['--arch'],
            args['--dist'],
            args['--timeout']
        )
    elif args['--watch']:
        timeout = int(args['--timeout'] or 30)
        if args['--filter-request-id']:
            response_reader(
                broker, timeout, response_filter_request_id(
                    args['--filter-request-id']
                )
            )
        else:
            response_reader(
                broker, timeout, response_filter_none()
            )


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


def get_build_dependencies(
    broker: Any, package: str, arch: str, dist: str, timeout_sec: int
) -> None:
    request_id = send_info_request(broker, package, arch, dist)
    info_response = info_reader(broker, request_id, timeout_sec)
    # TODO... handle response and ssh cat the solver file
    CBDisplay.print_yaml(info_response)


def response_filter_request_id(request_id: str) -> Callable:
    """
    Create callback closure for response_reader and
    filter responses by given request_id

    :param str request_id: request UUID

    :return: response_reader Callable

    :rtype: Callable
    """
    def func(response: Dict) -> None:
        if response['request_id'] == request_id:
            CBDisplay.print_yaml(response)
    return func


def response_filter_none() -> Callable:
    """
    Create callback closure for response_reader, all messages

    :return: response_reader Callable

    :rtype: Callable
    """
    def func(response: Dict) -> None:
        CBDisplay.print_yaml(response)
    return func


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
        Callback method for response record
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


def send_info_request(
    broker: Any, package: str, arch: str, dist: str
) -> str:
    info_request = CBInfoRequest()
    info_request.set_info_request(package, arch, dist)
    broker.send_info_request(info_request)
    broker.close()
    return info_request.get_data()['request_id']


def info_reader(broker: Any, request_id: str, timeout_sec: int) -> Dict:
    """
    Read from the cloud builder info response queue.
    In case multiple info services responds to the package
    only the record of the latest timestamp will be
    used

    :param CBMessageBroker broker: broker instance
    :param int timeout_sec:
        Wait time_sec seconds of inactivity on the message
        broker before return.
    :param Callable func:
        Callback method for response record
    """
    info_records = []
    try:
        while(True):
            message = None
            for message in broker.read(
                topic=Defaults.get_info_response_queue_name(),
                group=f'cb-ctl:{os.getpid()}',
                timeout_ms=timeout_sec * 1000
            ):
                response = broker.validate_info_response(
                    message.value
                )
                if response:
                    broker.acknowledge()
                    if response['request_id'] == request_id:
                        info_records.append(response)
            if not message:
                break
    finally:
        broker.close()

    if not info_records:
        final_info_record = {}
    elif len(info_records) == 1:
        final_info_record = info_records[0]
    else:
        latest_timestamp = get_datetime_from_utc_timestamp(
            info_records[0]['utc_modification_time']
        )
        for info_record in info_records:
            timestamp = get_datetime_from_utc_timestamp(
                info_record['utc_modification_time']
            )
            latest_timestamp = max((timestamp, latest_timestamp))
        for info_record in info_records:
            if info_record['utc_modification_time'] == format(latest_timestamp):
                final_info_record = info_record
    return final_info_record


def get_datetime_from_utc_timestamp(timestamp: str) -> datetime:
    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
