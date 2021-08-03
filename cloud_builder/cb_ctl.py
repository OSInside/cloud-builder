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
       cb-ctl --build=<package> --project-path=<path> --arch=<name> --dist=<name> --runner-group=<name>
           [--clean]
       cb-ctl --build-dependencies=<package> --project-path=<path> --arch=<name> --dist=<name>
           [--timeout=<time_sec>]
       cb-ctl --build-log=<package> --project-path=<path> --arch=<name> --dist=<name>
           [--timeout=<time_sec>]
       cb-ctl --build-info=<package> --project-path=<path> --arch=<name> --dist=<name>
           [--timeout=<time_sec>]
       cb-ctl --get-binaries=<package> --project-path=<path> --arch=<name> --dist=<name> --target-dir=<dir>
           [--timeout=<time_sec>]
       cb-ctl --watch
           [--filter-request-id=<uuid>]
           [--filter-service-name=<name>]
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

    --runner-group=<name>
        Send build request to specified runner group

    --build-dependencies=<package>
        Provide latest build root dependency information

    --build-log=<package>
        Provide latest raw package build log

    --build-info=<package>
        Provide latest build result and status information

    --get-binaries=<package>
        Download latest binary packages

    --target-dir=<dir>
        Name of target directory for get-binaries download

    --watch
        Watch response messages of the cloud builder system

    --filter-request-id=<uuid>
        Filter messages by given request UUID

    --filter-service-name=<name>
        Filter messages by given service name. Allowed
        service names are:
        * cb-fetch
        * cb-info
        * cb-run
        * cb-prepare
        * cb-scheduler

    --timeout=<time_sec>
        Wait time_sec seconds of inactivity on the message
        broker before return. Default: 30sec

    --clean
        Delete package buildroot if present on the runner
        before building the package
"""
import os
import yaml
import json
import logging
from docopt import docopt
from datetime import datetime
from cerberus import Validator
from typing import (
    Any, Dict, Callable
)

from cloud_builder.version import __version__
from cloud_builder.defaults import Defaults
from cloud_builder.broker import CBMessageBroker
from cloud_builder.package_request.package_request import CBPackageRequest
from cloud_builder.info_request.info_request import CBInfoRequest
from cloud_builder.utils.display import CBDisplay
from cloud_builder.config.cbctl_schema import cbctl_config_schema
from cloud_builder.logger import CBLogger

from cloud_builder.exceptions import (
    exception_handler,
    CBConfigFileNotFoundError,
    CBConfigFileValidationError
)

from kiwi.command import Command
from kiwi.path import Path


@exception_handler
def main() -> None:
    """
    cb-ctl - cloud builder control utility
    """
    kiwi_log = logging.getLogger('kiwi')
    kiwi_log.setLevel(logging.INFO)

    args = docopt(
        __doc__,
        version='CB (ctl) version ' + __version__,
        options_first=True
    )

    config = get_config()

    broker = CBMessageBroker.new(
        'kafka', config_file=Defaults.get_broker_config()
    )

    if args['--build']:
        build_package(
            broker,
            args['--build'],
            args['--project-path'],
            args['--arch'],
            args['--dist'],
            args['--runner-group'],
            bool(args['--clean'])
        )
    elif args['--build-dependencies']:
        get_build_dependencies(
            broker,
            args['--build-dependencies'],
            args['--project-path'],
            args['--arch'],
            args['--dist'],
            int(args['--timeout'] or 30),
            config
        )
    elif args['--build-log']:
        get_build_log(
            broker,
            args['--build-log'],
            args['--project-path'],
            args['--arch'],
            args['--dist'],
            int(args['--timeout'] or 30),
            config
        )
    elif args['--build-info']:
        get_build_info(
            broker,
            args['--build-info'],
            args['--project-path'],
            args['--arch'],
            args['--dist'],
            int(args['--timeout'] or 30)
        )
    elif args['--get-binaries']:
        fetch_binaries(
            broker,
            args['--get-binaries'],
            args['--project-path'],
            args['--arch'],
            args['--dist'],
            int(args['--timeout'] or 30),
            args['--target-dir'],
            config
        )
    elif args['--watch']:
        timeout = int(args['--timeout'] or 30)
        if args['--filter-request-id']:
            _response_reader(
                broker, timeout, watch_filter_request_id(
                    args['--filter-request-id']
                )
            )
        elif args['--filter-service-name']:
            _response_reader(
                broker, timeout, watch_filter_service_name(
                    args['--filter-service-name']
                )
            )
        else:
            _response_reader(
                broker, timeout, watch_filter_none()
            )


def get_config() -> Dict:
    try:
        with open(Defaults.get_cb_ctl_config(), 'r') as config_fd:
            config = yaml.safe_load(config_fd)
    except Exception as issue:
        raise CBConfigFileNotFoundError(issue)
    validator = Validator(cbctl_config_schema)
    validator.validate(config, cbctl_config_schema)
    if validator.errors:
        raise CBConfigFileValidationError(
            'ValidationError for {0!r}: {1!r}'.format(config, validator.errors)
        )
    return config


def build_package(
    broker: Any, package: str, project_path: str,
    arch: str, dist: str, runner_group: str, clean_buildroot: bool
) -> None:
    status_flags = Defaults.get_status_flags()
    package_request = CBPackageRequest()
    package_request.set_package_build_request(
        _get_package_path(project_path, package),
        arch, dist, runner_group,
        status_flags.package_rebuild_clean if clean_buildroot else
        status_flags.package_rebuild
    )
    broker.send_package_request(package_request)
    CBDisplay.print_json(package_request.get_data())
    broker.close()


def get_build_dependencies(
    broker: Any, package: str, project_path: str, arch: str, dist: str,
    timeout_sec: int, config: Dict
) -> None:
    solver_data = _get_info_response_file(
        broker, package, project_path, arch, dist,
        timeout_sec, config, 'solver_file'
    )
    if solver_data:
        CBDisplay.print_json(json.loads(solver_data))


def get_build_log(
    broker: Any, package: str, project_path: str, arch: str, dist: str,
    timeout_sec: int, config: Dict
) -> None:
    build_log_data = _get_info_response_file(
        broker, package, project_path, arch, dist,
        timeout_sec, config, 'log_file'
    )
    if build_log_data:
        CBDisplay.print_raw(build_log_data)


def get_build_info(
    broker: Any, package: str, project_path: str, arch: str, dist: str,
    timeout_sec: int
) -> None:
    CBDisplay.print_json(
        get_info(broker, package, project_path, arch, dist, timeout_sec)
    )


def fetch_binaries(
    broker: Any, package: str, project_path: str, arch: str, dist: str,
    timeout_sec: int, target_dir, config: Dict
) -> None:
    log = CBLogger.get_logger()
    info_response = get_info(
        broker, package, project_path, arch, dist, timeout_sec
    )
    if info_response:
        runner_ip = info_response['source_ip']
        ssh_user = config['runner']['ssh_user']
        ssh_pkey_file = config['runner']['ssh_pkey_file']
        Path.create(target_dir)
        for binary in info_response['binary_packages']:
            log.info(f'Fetching {binary} -> {target_dir}')
            Command.run(
                [
                    'scp', '-i', ssh_pkey_file,
                    '-o', 'StrictHostKeyChecking=accept-new',
                    f'{ssh_user}@{runner_ip}:{binary}',
                    target_dir
                ]
            )


def watch_filter_service_name(service_name: str) -> Callable:
    """
    Create callback closure for _response_reader and
    filter responses by given service name

    :param str service_name:
        one of cb-fetch, cb-info, cb-run, cb-prepare, cb-scheduler

    :rtype: Callable
    """
    def func(response: Dict) -> None:
        service_id = {
            'cb-fetch': 'CBFetch',
            'cb-info': 'CBInfo',
            'cb-run': 'CBRun',
            'cb-prepare': 'CBPrepare',
            'cb-scheduler': 'CBScheduler'
        }
        if response['identity'].startswith(service_id[service_name]):
            CBDisplay.print_json(response)
    return func


def watch_filter_request_id(request_id: str) -> Callable:
    """
    Create callback closure for _response_reader and
    filter responses by given request_id

    :param str request_id: request UUID

    :rtype: Callable
    """
    def func(response: Dict) -> None:
        if response['request_id'] == request_id:
            CBDisplay.print_json(response)
    return func


def watch_filter_none() -> Callable:
    """
    Create callback closure for _response_reader, all messages

    :rtype: Callable
    """
    def func(response: Dict) -> None:
        CBDisplay.print_json(response)
    return func


def get_info(
    broker: Any, package: str, project_path: str, arch: str, dist: str,
    timeout_sec: int
) -> Dict:
    request_id = _send_info_request(
        broker, _get_package_path(project_path, package), arch, dist
    )
    return _info_reader(broker, request_id, timeout_sec)


def _get_info_response_file(
    broker: Any, package: str, project_path: str, arch: str, dist: str,
    timeout_sec: int, config: Dict, response_file_name
) -> str:
    info_response = get_info(
        broker, package, project_path, arch, dist, timeout_sec
    )
    if info_response:
        response_file = info_response[response_file_name]
        runner_ip = info_response['source_ip']
        ssh_user = config['runner']['ssh_user']
        ssh_pkey_file = config['runner']['ssh_pkey_file']
        return Command.run(
            [
                'ssh', '-i', ssh_pkey_file,
                '-o', 'StrictHostKeyChecking=accept-new',
                f'{ssh_user}@{runner_ip}',
                'cat', response_file
            ]
        ).output
    return ''


def _response_reader(
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


def _send_info_request(
    broker: Any, package_path: str, arch: str, dist: str
) -> str:
    info_request = CBInfoRequest()
    info_request.set_info_request(package_path, arch, dist)
    broker.send_info_request(info_request)
    broker.close()
    return info_request.get_data()['request_id']


def _info_reader(broker: Any, request_id: str, timeout_sec: int) -> Dict:
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
        latest_timestamp = _get_datetime_from_utc_timestamp(
            info_records[0]['utc_modification_time']
        )
        for info_record in info_records:
            timestamp = _get_datetime_from_utc_timestamp(
                info_record['utc_modification_time']
            )
            latest_timestamp = max((timestamp, latest_timestamp))
        for info_record in info_records:
            if info_record['utc_modification_time'] == format(latest_timestamp):
                final_info_record = info_record
    return final_info_record


def _get_datetime_from_utc_timestamp(timestamp: str) -> datetime:
    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")


def _get_package_path(project_path: str, package_name: str) -> str:
    return os.path.join(
        'projects', project_path, package_name,
    )
