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
       cb-ctl --build-package-local --dist=<name>
           [--clean]
           [--debug]
       cb-ctl --build-package=<package> --project-path=<path> --arch=<name> --dist=<name> --runner-group=<name>
           [--debug]
       cb-ctl --build-image-local --selection=<name>
           [--debug]
       cb-ctl --build-image=<image> --project-path=<path> --arch=<name> --runner-group=<name> --selection=<name>
           [--debug]
       cb-ctl --build-dependencies=<package│image> --project-path=<path> --arch=<name> (--dist=<name>|--selection=<name>)
           [--timeout=<time_sec>]
           [--debug]
       cb-ctl --build-dependencies-local --arch=<name> (--dist=<name>|--selection=<name>)
           [--debug]
       cb-ctl --build-log=<package│image> --project-path=<path> --arch=<name> (--dist=<name>|--selection=<name>)
           [--keep-open]
           [--timeout=<time_sec>]
           [--debug]
       cb-ctl --build-info=<package│image> --project-path=<path> --arch=<name> (--dist=<name>|--selection=<name>)
           [--timeout=<time_sec>]
           [--debug]
       cb-ctl --get-binaries=<package│image> --project-path=<path> --arch=<name> --target-dir=<dir> (--dist=<name>|--selection=<name>)
           [--timeout=<time_sec>]
           [--debug]
       cb-ctl --watch
           [--filter-request-id=<uuid>]
           [--filter-service-name=<name>]
           [--timeout=<time_sec>]
           [--debug]

options:
    --build-package=<package>
        Create a request to build the given package.
        The provided argument is appended to the
        project-path and forms the directory path
        to the package in the git repository

        projects/
          └── <project-path>/
                    └── <package>/...

        Please note, the root directory is by convention
        a fixed name set to 'projects'

    --build-package-local
        Build package from local checkout. The package
        sources will be looked up from the current working
        directory

    --build-image-local
        Build image from local checkout. The image sources
        will be looked up from the current working directory

    --build-image=<image>
        Create a request to build the given image.
        The provided image argument is used in the same
        way as the package argument from --build-package

    --project-path=<path>
        Project path that points to the package in the git.
        See the above structure example

    --arch=<name>
        Target architecture name

    --dist=<name>
        Target distribution name for package builds

    --selection=<name>
        Image selection name for image builds

    --runner-group=<name>
        Send build request to specified runner group

    --build-dependencies=<package|image>
        Provide latest build root dependency information

    --build-dependencies-local
        Calculate build dependencies now and on the local system

    --build-log=<package│image>
        Provide latest raw package build log

    --build-info=<package│image>
        Provide latest build result and status information

    --get-binaries=<package│image>
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
        * cb-image

    --timeout=<time_sec>
        Wait time_sec seconds of inactivity on the message
        broker before return. Default: 10sec

    --clean
        Delete package buildroot if present on the runner
        before building the package

    --keep-open
        Use tail -f to open the log file on the runner

    --debug
        Set log level to DEBUG for cloud-builder and kiwi
        namespaces
"""
import time
import os
import sys
import yaml
import json
import logging
import platform
from docopt import docopt
from datetime import datetime
from cerberus import Validator
from typing import (
    Any, Dict, Callable
)

from cloud_builder.version import __version__
from cloud_builder.defaults import Defaults
from cloud_builder.broker import CBMessageBroker
from cloud_builder.build_request.build_request import CBBuildRequest
from cloud_builder.project_metadata.project_metadata import CBProjectMetaData
from cloud_builder.info_request.info_request import CBInfoRequest
from cloud_builder.utils.display import CBDisplay
from cloud_builder.config.cbctl_schema import cbctl_config_schema
from cloud_builder.cb_scheduler import (
    create_package_run_script,
    create_image_run_script,
    is_request_valid
)
from cloud_builder.cb_prepare import resolve_build_dependencies

from cloud_builder.exceptions import (
    exception_handler,
    CBConfigFileNotFoundError,
    CBConfigFileValidationError,
    CBProjectMetadataError,
    CBExecutionError,
    CBParameterError
)

from kiwi.command import Command
from kiwi.privileges import Privileges
from kiwi.path import Path

kiwi_log = logging.getLogger('kiwi')
log = logging.getLogger('cloud_builder')


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
    default_timeout = 10

    log_level = logging.DEBUG if args['--debug'] else logging.INFO
    kiwi_log.setLevel(log_level)
    log.setLevel(log_level)

    if args['--build-package']:
        build_package(
            get_broker(),
            args['--build-package'],
            args['--project-path'],
            args['--arch'],
            args['--dist'],
            args['--runner-group']
        )
    elif args['--build-package-local']:
        build_package_local(
            args['--dist'],
            bool(args['--clean'])
        )
    elif args['--build-image-local']:
        build_image_local(args['--selection'])
    elif args['--build-image']:
        build_image(
            get_broker(),
            args['--build-image'],
            args['--project-path'],
            args['--arch'],
            args['--selection'],
            args['--runner-group']
        )
    elif args['--build-dependencies']:
        get_build_dependencies(
            get_broker(),
            args['--build-dependencies'],
            args['--project-path'],
            args['--arch'],
            args['--dist'],
            args['--selection'],
            int(args['--timeout'] or default_timeout),
            get_config()
        )
    elif args['--build-dependencies-local']:
        get_build_dependencies_local(
            args['--dist'],
            args['--selection'],
            args['--arch']
        )
    elif args['--build-log']:
        get_build_log(
            get_broker(),
            args['--build-log'],
            args['--project-path'],
            args['--arch'],
            args['--dist'],
            args['--selection'],
            int(args['--timeout'] or default_timeout),
            args['--keep-open'],
            get_config()
        )
    elif args['--build-info']:
        get_build_info(
            get_broker(),
            args['--build-info'],
            args['--project-path'],
            args['--arch'],
            args['--dist'],
            args['--selection'],
            int(args['--timeout'] or default_timeout),
            get_config()
        )
    elif args['--get-binaries']:
        fetch_binaries(
            get_broker(),
            args['--get-binaries'],
            args['--project-path'],
            args['--arch'],
            args['--dist'],
            args['--selection'],
            int(args['--timeout'] or default_timeout),
            args['--target-dir'],
            get_config()
        )
    elif args['--watch']:
        timeout = int(args['--timeout'] or default_timeout)
        if args['--filter-request-id']:
            _response_reader(
                get_broker(), timeout, watch_filter_request_id(
                    args['--filter-request-id']
                )
            )
        elif args['--filter-service-name']:
            _response_reader(
                get_broker(), timeout, watch_filter_service_name(
                    args['--filter-service-name']
                )
            )
        else:
            _response_reader(
                get_broker(), timeout, watch_filter_none()
            )


def get_broker() -> Any:
    broker_type = 'kafka'
    config = get_config()
    broker_config_file = Defaults.get_broker_config()
    config_settings = config.get('settings')
    log.debug(config_settings)
    if config_settings:
        if config_settings.get('use_control_plane_as_proxy') is True:
            broker_type = 'kafka_proxy'
            broker_config_file = ''
    return CBMessageBroker.new(
        broker_type, config_file=broker_config_file, custom_args=config
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
    arch: str, dist: str, runner_group: str
) -> None:
    status_flags = Defaults.get_status_flags()
    package_request = CBBuildRequest()
    package_request.set_package_build_request(
        _get_target_path(project_path, package),
        arch, dist, runner_group,
        status_flags.package_rebuild
    )
    broker.send_build_request(package_request)
    CBDisplay.print_json(package_request.get_data())
    broker.close()


def build_image_local(selection: str) -> None:
    Privileges.check_for_root_permissions()

    status_flags = Defaults.get_status_flags()
    image_source_path = os.getcwd()
    image_request = CBBuildRequest()
    image_request.set_image_build_request(
        image=image_source_path,
        arch=platform.machine(),
        selection=selection,
        runner_group='local',
        action=status_flags.image_local
    )

    project_config = _check_project_config_from_working_directory(
        image_request
    )

    image_build_run = [
        'bash', create_image_run_script(
            image_request.get_data(), project_config, local_build=True
        )
    ]
    exit_code = os.WEXITSTATUS(
        os.system(' '.join(image_build_run))
    )
    sys.exit(exit_code)


def build_package_local(dist: str, clean_buildroot: bool) -> None:
    Privileges.check_for_root_permissions()

    status_flags = Defaults.get_status_flags()
    package_source_path = os.getcwd()
    package_request = CBBuildRequest()
    package_request.set_package_build_request(
        package=package_source_path,
        arch=platform.machine(),
        dist=dist,
        runner_group='local',
        action=status_flags.package_local
    )

    _check_project_config_from_working_directory(package_request)

    package_build_run = [
        'bash', create_package_run_script(
            package_request.get_data(), clean_buildroot,
            local_build=True
        )
    ]
    exit_code = os.WEXITSTATUS(
        os.system(' '.join(package_build_run))
    )
    sys.exit(exit_code)


def build_image(
    broker: Any, image: str, project_path: str,
    arch: str, selection: str, runner_group: str
) -> None:
    status_flags = Defaults.get_status_flags()
    image_request = CBBuildRequest()
    image_request.set_image_build_request(
        _get_target_path(project_path, image),
        arch, selection, runner_group,
        status_flags.image_rebuild
    )
    broker.send_build_request(image_request)
    CBDisplay.print_json(image_request.get_data())
    broker.close()


def get_build_dependencies(
    broker: Any, target: str, project_path: str, arch: str,
    dist: str, selection: str, timeout_sec: int, config: Dict
) -> None:
    solver_data = _get_info_response_file(
        broker, target, project_path, arch, dist, selection,
        timeout_sec, config, 'dependencies'
    )
    if solver_data:
        CBDisplay.print_json(json.loads(solver_data))


def get_build_dependencies_local(
    dist: str, selection_name: str, arch: str
) -> None:
    Privileges.check_for_root_permissions()

    target_source_path = os.getcwd()

    project_config = _check_project_config_from_working_directory()
    if dist:
        profile_list = [f'{dist}.{arch}']
    elif selection_name:
        profile_list = []
        for target in project_config.get('images') or []:
            selection = target['selection']
            if selection['name'] == selection_name:
                profile_list = selection.get('profiles') or []

    solver_result = resolve_build_dependencies(
        source_path=target_source_path,
        profile_list=profile_list,
        resolve_for_image_source=True if selection_name else False
    )
    if solver_result['solver_data']:
        CBDisplay.print_json(
            solver_result['solver_data']
        )
    else:
        CBDisplay.print_raw(
            solver_result['solver_log']
        )


def get_build_log(
    broker: Any, target: str, project_path: str, arch: str,
    dist: str, selection: str, timeout_sec: int, keep_open: bool,
    config: Dict
) -> None:
    build_log_data = _get_info_response_file(
        broker, target, project_path, arch, dist, selection,
        timeout_sec, config, 'logs', keep_open
    )
    if build_log_data:
        CBDisplay.print_raw(build_log_data)


def get_build_info(
    broker: Any, target: str, project_path: str, arch: str,
    dist: str, selection: str, timeout_sec: int, config: Dict
) -> None:
    CBDisplay.print_json(
        get_info(
            broker, target, project_path, arch, dist, selection,
            timeout_sec, config
        )
    )


def fetch_binaries(
    broker: Any, target: str, project_path: str, arch: str,
    dist: str, selection: str, timeout_sec: int, target_dir, config: Dict
) -> None:
    info_response = get_info(
        broker, target, project_path, arch, dist, selection,
        timeout_sec, config
    )
    if info_response:
        runner_ip = info_response['source_ip']
        ssh_user = config['cluster']['ssh_user']
        ssh_pkey_file = config['cluster']['ssh_pkey_file']
        Path.create(target_dir)
        for binary in info_response['binary_packages']:
            log.debug(f'Fetching {binary} -> {target_dir}')
            scp_call = [
                'scp', '-i', ssh_pkey_file,
                '-o', 'StrictHostKeyChecking=accept-new',
                f'{ssh_user}@{runner_ip}:{binary}',
                target_dir
            ]
            scp_call_command = ' '.join(scp_call)
            exit_code = os.WEXITSTATUS(
                os.system(scp_call_command)
            )
            if exit_code != 0:
                raise CBExecutionError(
                    f'Failed to run: {scp_call_command}'
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
            'cb-scheduler': 'CBScheduler',
            'cb-image': 'CBImage'
        }
        if service_name not in service_id:
            raise CBParameterError(
                f'Service name {service_name!r} not found'
            )
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
    broker: Any, target: str, project_path: str, arch: str,
    dist: str, selection: str, timeout_sec: int, config: Dict
) -> Dict:
    if dist:
        request_id = _send_package_info_request(
            broker, _get_target_path(project_path, target), arch, dist
        )
    else:
        request_id = _send_image_info_request(
            broker, _get_target_path(project_path, target), arch, selection
        )
    return _info_reader(broker, request_id, timeout_sec, config)


def _get_info_response_file(
    broker: Any, target: str, project_path: str, arch: str,
    dist: str, selection: str, timeout_sec: int, config: Dict,
    response_file_id: str, keep_open: bool = False
) -> str:
    info_response = get_info(
        broker, target, project_path, arch, dist, selection,
        timeout_sec, config
    )
    if info_response:
        runner_ip = info_response['source_ip']
        ssh_user = config['cluster']['ssh_user']
        ssh_pkey_file = config['cluster']['ssh_pkey_file']
        ssh_runner = [
            'ssh', '-i', ssh_pkey_file,
            '-o', 'StrictHostKeyChecking=accept-new',
            f'{ssh_user}@{runner_ip}'
        ]
        response_file_list = []
        if response_file_id == 'logs' and selection:
            # image build log
            build_log_file = _get_file_from_response(
                info_response, 'log_file'
            )
            if build_log_file:
                response_file_list.append(build_log_file)
        elif response_file_id == 'logs' and dist:
            # package build logs
            prepare_log_file = _get_file_from_response(
                info_response, 'prepare_log_file'
            )
            if prepare_log_file:
                response_file_list.append(prepare_log_file)
            build_log_file = _get_file_from_response(
                info_response, 'log_file'
            )
            if build_log_file:
                response_file_list.append(build_log_file)
        elif response_file_id == 'dependencies':
            # image or package build dependencies
            solver_log_file = _get_file_from_response(
                info_response, 'solver_file'
            )
            if solver_log_file:
                response_file_list.append(solver_log_file)

        if response_file_list:
            if not keep_open:
                return Command.run(
                    ssh_runner + [
                        'cat'
                    ] + response_file_list
                ).output
            else:
                os.system(
                    ' '.join(
                        ssh_runner + [
                            'tail', '-f',
                        ] + response_file_list
                    )
                )
    return ''


def _get_file_from_response(info_response: Dict, name: str) -> str:
    if name == 'prepare_log_file':
        filename = info_response['package'][name]
    else:
        filename = info_response[name]
    if filename == 'none':
        log.warning(f'Response record has no information for: {name}')
        filename = ''
    return filename


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
                response = broker.validate_build_response(
                    message.value
                )
                if response:
                    func(response)
            if not message:
                break
    finally:
        broker.close()


def _send_package_info_request(
    broker: Any, target_path: str, arch: str, dist: str
) -> str:
    info_request = CBInfoRequest()
    info_request.set_package_info_request(target_path, arch, dist)
    broker.send_info_request(info_request)
    broker.close()
    return info_request.get_data()['request_id']


def _send_image_info_request(
    broker: Any, target_path: str, arch: str, selection: str
) -> str:
    info_request = CBInfoRequest()
    info_request.set_image_info_request(target_path, arch, selection)
    broker.send_info_request(info_request)
    broker.close()
    return info_request.get_data()['request_id']


def _info_reader(
    broker: Any, request_id: str, timeout_sec: int, config: Dict
) -> Dict:
    """
    Read from the cloud builder info response queue.
    In case multiple info services responds to the package/image
    only the record of the latest timestamp will be
    used

    :param CBMessageBroker broker: broker instance
    :param int timeout_sec:
        Wait time_sec seconds of inactivity on the message
        broker before return.
    :param dict config: cbctl.yml config hash
    :param Callable func:
        Callback method for response record
    """
    stop_reading_at = config['cluster'].get('runner_count') or 0
    response_count = 0
    info_records = []
    try:
        timeout_loop_start = time.time()
        while time.time() < timeout_loop_start + timeout_sec + 1 and (
            stop_reading_at == 0 or stop_reading_at > response_count
        ):
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
                    if response['request_id'] == request_id:
                        broker.acknowledge()
                        if response['utc_modification_time'] != 'none':
                            info_records.append(response)
                        response_count += 1
            if not message:
                break
    finally:
        broker.close()

    if stop_reading_at > 0 and response_count != stop_reading_at:
        log.warning(
            'runner count set to {0} but got {1} responses'.format(
                stop_reading_at, response_count
            )
        )

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


def _get_target_path(project_path: str, target_name: str) -> str:
    return os.path.join(
        'projects', project_path, target_name,
    )


def _check_project_config_from_working_directory(
    request: CBBuildRequest = None
) -> Dict:
    target_source_path = os.getcwd()
    if request:
        validated_request = is_request_valid(
            target_source_path, request.get_data()
        )
        if not validated_request.is_valid \
           and validated_request.response:
            CBDisplay.print_json(validated_request.response.get_data())
        project_config = validated_request.project_config
    else:
        project_config = CBProjectMetaData.get_project_config(
            target_source_path
        )
    if not project_config:
        raise CBProjectMetadataError(
            f'No or invalid package/image metadata in {target_source_path}'
        )
    return project_config
