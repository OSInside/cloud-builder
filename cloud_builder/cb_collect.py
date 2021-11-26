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
usage: cb-collect -h | --help
       cb-collect --project=<github_project> --ssh-pkey=<ssh_pkey_file>
           [--ssh-user=<user>]
           [--timeout=<time_sec>]
           [--update-interval=<time_sec>]
           [--runners=<runner_count>]

options:
    --project=<github_project>
        git clone source URI to fetch project with
        packages managed to build in cloud builder

    --ssh-pkey=<ssh_pkey_file>
        Path to ssh private key file to access runner data

    --ssh-user=<user>
        User name to access runners via ssh, defaults to: ec2-user

    --timeout=<time_sec>
        Wait time_sec seconds of inactivity on the message
        broker before return. Default: 30sec

    --update-interval=<time_sec>
        Update interval to ask for new packages/images
        Default: 30sec

    --runners=<runner_count>
        Number of runners in the cluster
"""
import logging
import os
import time
import yaml
from threading import (
    Thread, Lock
)
from datetime import datetime
from docopt import docopt
from cloud_builder.version import __version__
from cloud_builder.cloud_logger import CBCloudLogger
from cloud_builder.identity import CBIdentity
from cloud_builder.exceptions import exception_handler
from cloud_builder.defaults import Defaults
from cloud_builder.project_metadata.project_metadata import CBProjectMetaData
from cloud_builder.info_request.info_request import CBInfoRequest
from cloud_builder.broker import CBMessageBroker
from kiwi.command import Command
from kiwi.logger import Logger
from kiwi.privileges import Privileges
from kiwi.path import Path
from typing import (
    Dict, List, Any, Optional, NamedTuple
)

repo_metadata = NamedTuple(
    'repo_metadata', [
        ('repo_type', str),
        ('repo_file', str),
        ('repo_path', str)
    ]
)


@exception_handler
def main() -> None:
    """
    cb-collect - fetches/updates a git repository and
    collects build results of package/image sources as organized
    in the git tree. Each project in the git tree will
    be represented as a package repository.

    The tree structure of the repository tree follows the
    git project structure like in the following example:

    REPO_ROOT
    ├── ...
    ├── PROJECT_A
    │   └── SUB_PROJECT
    │       └── REPO_DATA_AND_REPO_METADATA
    └── PROJECT_B
        └── REPO_DATA_AND_REPO_METADATA

    The REPO_ROOT could be served to the public via a
    web server e.g apache such that the repos will be
    consumable for the outside world and package
    managers
    """
    args = docopt(
        __doc__,
        version='CB (collect) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()

    log = CBCloudLogger('CBCollect', '(system)')
    log.set_logfile()

    kiwi_log: Logger = logging.getLogger('kiwi')
    kiwi_log.set_logfile(Defaults.get_cb_logfile())

    project_dir = Defaults.get_runner_project_dir()
    Path.wipe(project_dir)
    Command.run(
        ['git', 'clone', args['--project'], project_dir]
    )

    broker = CBMessageBroker.new(
        'kafka', config_file=Defaults.get_broker_config()
    )
    build_repos(
        broker, int(args['--timeout'] or 30),
        args['--ssh-pkey'], args['--ssh-user'] or 'ec2-user',
        int(args['--update-interval'] or 30),
        int(args['--runners'] or 0),
        log
    )


def update_project() -> None:
    Command.run(
        ['git', '-C', Defaults.get_runner_project_dir(), 'pull']
    )


def build_project_tree() -> Dict[str, List]:
    """
    Represent the git project tree to be simply consumable

    :return:
        Dictionary with package/image names per project e.g

        .. code:: python

           {
               'cloud-builder-projects/projects/MS': [
                   'python-kiwi_boxed_plugin',
                   'xclock'
               ]
           }

    :rtype: Dict
    """
    projects_tree: Dict[str, List] = {}
    projects_root = os.path.join(
        Defaults.get_runner_project_dir(), 'projects'
    )
    for root, dirs, files in os.walk(projects_root):
        for dirname in dirs:
            if dirname == Defaults.get_cloud_builder_meta_dir():
                project_name = os.path.dirname(root)
                package_or_image_name = os.path.basename(root)
                if project_name in projects_tree:
                    projects_tree[project_name].append(package_or_image_name)
                else:
                    projects_tree[project_name] = [package_or_image_name]
    return projects_tree


def send_project_info_requests(
    broker: Any, projects_tree: Dict[str, List], log: CBCloudLogger
) -> List[str]:
    """
    Walk through the packages/images and send info requests

    :param Any broker: Instance of broker factory

    :return: List of request IDs

    :rtype: List
    """
    requuest_ids: List[str] = []
    for project in sorted(projects_tree.keys()):
        for package_or_image in projects_tree[project]:
            project_path = os.path.join(project, package_or_image)
            project_config = CBProjectMetaData.get_project_config(
                project_path, log, CBIdentity.get_request_id()
            )
            if project_config:
                for target in project_config.get('distributions') or []:
                    info_request = CBInfoRequest()
                    info_request.set_package_info_request(
                        project_path.replace(
                            Defaults.get_runner_project_dir(), ''
                        ), target['arch'], target['dist']
                    )
                    broker.send_info_request(info_request)
                    requuest_ids.append(
                        info_request.get_data()['request_id']
                    )
                for target in project_config.get('images') or []:
                    info_request = CBInfoRequest()
                    info_request.set_image_info_request(
                        project_path.replace(
                            Defaults.get_runner_project_dir(), ''
                        ), target['arch'], target['selection']['name']
                    )
                    broker.send_info_request(info_request)
                    requuest_ids.append(
                        info_request.get_data()['request_id']
                    )
    return requuest_ids


def group_info_response(
    broker: Any, request_id_list: List[str], timeout_sec: int,
    runner_count: int, log: CBCloudLogger
) -> Dict:
    """
    Watch on the info_response queue for information
    matching the given request IDs and group the results
    by their runner IP and project path

    :param Any broker: Instance of broker factory
    :param List request_id_list: list of matching request IDs
    :param int timeout: read timeout in sec on cb-info response
    :param int runner_count: number of runners
    :param CBCloudLogger log: logger object

    :return:
        Dictionary of IP groups and their data to fetch

        .. code:: python

            {
                project_id: {
                    source_ip: {
                        [
                            binary_packages
                        ]
                    }
                }
            }

    :rtype: Dict
    """
    stop_reading_at = len(request_id_list) * runner_count
    response_count = 0
    info_records: Dict[str, List] = {}
    # Read package info responses and group them by a unique id
    # consisting out of: project-package-arch-dist information
    try:
        timeout_loop_start = time.time()
        while time.time() < timeout_loop_start + timeout_sec + 1 and (
            stop_reading_at == 0 or stop_reading_at > response_count
        ):
            message = None
            for message in broker.read(
                topic=Defaults.get_info_response_queue_name(),
                group='cb-collect', timeout_ms=timeout_sec * 1000
            ):
                response = broker.validate_info_response(
                    message.value
                )
                if response:
                    if response['request_id'] in request_id_list:
                        broker.acknowledge()
                        if response['utc_modification_time'] != 'none':
                            # A utc_modification_time set to none, indicates
                            # that this info response was sent from an info
                            # service which has no data for the requested
                            # package/image (info server configured with
                            # --always-respond). These responses we ignore for
                            # the collector, but they are important to identify
                            # the time when all runners have responded.
                            project_id = ''
                            if 'package' in response:
                                project_id = '{0}_{1}_{2}'.format(
                                    response['project'],
                                    response['package']['arch'],
                                    response['package']['dist']
                                )
                            elif 'image' in response:
                                project_id = '{0}_{1}_{2}'.format(
                                    response['project'],
                                    response['image']['arch'],
                                    'image'
                                )
                            if project_id and project_id in info_records:
                                info_records[project_id].append(response)
                            elif project_id:
                                info_records[project_id] = [response]
                        response_count += 1
            if not message:
                break
    except Exception as issue:
        log.error(format(issue))
        return {}

    if stop_reading_at > 0 and response_count != stop_reading_at:
        log.warning(
            'expected {0}*{1} responses but got {2} responses'.format(
                len(request_id_list), runner_count, response_count
            )
        )

    # Walk through project_id grouped responses and take out the
    # latest available build. Group all data by project_id/source_ip
    runner_responses: Dict[str, Dict[str, List]] = {}
    for project in info_records.keys():
        response_list = info_records[project]
        if len(response_list) == 1:
            final_response = response_list[0]
        else:
            latest_timestamp = _get_datetime_from_utc_timestamp(
                response_list[0]['utc_modification_time']
            )
            for response in response_list:
                timestamp = _get_datetime_from_utc_timestamp(
                    response['utc_modification_time']
                )
                latest_timestamp = max((timestamp, latest_timestamp))
            for response in response_list:
                if response['utc_modification_time'] == format(
                    latest_timestamp
                ):
                    final_response = response

        if 'package' in final_response:
            target = final_response['package']['dist']
        elif 'image' in final_response:
            target = final_response['image']['selection']
        else:
            # not a package and not an image, ignore
            log.error(
                'project {0} is not a package or image, ignored'.format(
                    final_response['project']
                )
            )
            continue
        project_id = os.path.join(
            os.path.dirname(final_response['project']), target
        )
        if project_id not in runner_responses:
            runner_responses[project_id] = {}

        source_ip = final_response['source_ip']
        if source_ip not in runner_responses[project_id]:
            runner_responses[project_id][source_ip] = []

        project_package_name = os.path.basename(final_response['project'])
        for entry in final_response['binary_packages']:
            runner_responses[project_id][source_ip].append(
                f'{entry}|{project_package_name}'
            )
    return runner_responses


def build_repos(
    broker: Any, timeout: int, ssh_pkey_file: str, user: str,
    update_interval: int, runner_count: int, log: CBCloudLogger
) -> None:
    """
    Application loop - building project repositories

    :param Any broker: Instance of broker factory
    :param int timeout: Read timeout on info response queue
    """
    thread_lock = Lock()

    while(True):
        update_project()
        projects_tree = build_project_tree()
        request_id_list = send_project_info_requests(
            broker, projects_tree, log
        )
        runner_responses = group_info_response(
            broker, request_id_list, timeout, runner_count, log
        )
        if not runner_responses:
            log.info(
                f'No runners responded... sleeping {update_interval} sec'
            )
            time.sleep(update_interval)
            continue
        for project_id in runner_responses.keys():
            project_repo_thread = Thread(
                target=build_project_repo,
                args=(
                    project_id, runner_responses[project_id],
                    ssh_pkey_file, user, thread_lock, log
                )
            )
            project_repo_thread.start()

        # wait update_interval seconds before next round
        time.sleep(update_interval)


def cleanup_project_repo(
    repo_project_path: str, log: CBCloudLogger
) -> bool:
    """
    Delete project from repos if it was deleted from the git source

    :param str repo_project_path: Project path in repo
    :param CBCloudLogger log: logger
    """
    cleanup_performed = False
    if os.path.exists(repo_project_path):
        source_project = repo_project_path.replace(
            Defaults.get_repo_root(), Defaults.get_runner_project_dir()
        )
        if not os.path.exists(source_project):
            log.info(f'Deleting repos for project {repo_project_path!r}')
            Path.wipe(repo_project_path)
            cleanup_performed = True
    return cleanup_performed


def cleanup_project_repo_packages(
    repo_project_path: str, log: CBCloudLogger
) -> bool:
    """
    Delete packages from project repo if they were deleted
    from the git source

    :param str repo_project_path: Project path in repo
    :param CBCloudLogger log: logger
    """
    cleanup_performed = False
    project_files_name = f'{repo_project_path}/.project/files'
    if os.path.isfile(project_files_name):
        with open(project_files_name) as files_handle:
            project_files = yaml.safe_load(files_handle)
        source_project = repo_project_path.replace(
            Defaults.get_repo_root(), Defaults.get_runner_project_dir()
        )
        new_project_files = {}
        for package in project_files.keys():
            package_path = f'{source_project}/{package}'
            if not os.path.exists(package_path):
                log.info(f'Deleting {package!r} from repos')
                for target in project_files[package]:
                    for file in project_files[package][target]:
                        if os.path.isfile(file):
                            log.info(f'--> Deleting {file!r}')
                            os.unlink(file)
                            cleanup_performed = True
            else:
                new_project_files[package] = project_files[package]
        if cleanup_performed:
            with open(project_files_name, 'w') as files_handle:
                files_handle.write(
                    yaml.dump(new_project_files, default_flow_style=False)
                )
    return cleanup_performed


def cleanup_project_repo_packages_targets(
    repo_project_path: str, log: CBCloudLogger
) -> bool:
    """
    Delete packages from project repo that belongs to specific
    targets (dist or selection) if they were deleted from
    the git source metadata configuration

    :param str repo_project_path: Project path in repo
    :param CBCloudLogger log: logger
    """
    cleanup_performed = False
    project_files_name = f'{repo_project_path}/.project/files'
    if os.path.isfile(project_files_name):
        with open(project_files_name) as files_handle:
            project_files = yaml.safe_load(files_handle)
        source_project = repo_project_path.replace(
            Defaults.get_repo_root(), Defaults.get_runner_project_dir()
        )
        new_project_files: Dict[str, Dict[str, List]] = {}
        for package in project_files.keys():
            package_path = f'{source_project}/{package}'
            if os.path.exists(package_path):
                project_config = CBProjectMetaData.get_project_config(
                    package_path, log, CBIdentity.get_request_id()
                )
                target_names = []
                if project_config:
                    for target in project_config.get('distributions') or []:
                        target_names.append(target['dist'])
                    for target in project_config.get('images') or []:
                        target_names.append(target['selection']['name'])
                for target in project_files[package]:
                    if target not in target_names:
                        log.info(
                            f'Deleting {package!r} for {target!r} from repos'
                        )
                        for file in project_files[package][target]:
                            if os.path.isfile(file):
                                log.info(f'--> Deleting {file!r}')
                                os.unlink(file)
                                cleanup_performed = True
                    else:
                        if package not in new_project_files:
                            new_project_files[package] = {}
                        new_project_files[package][target] = \
                            project_files[package][target]
        if cleanup_performed:
            with open(project_files_name, 'w') as files_handle:
                files_handle.write(
                    yaml.dump(new_project_files, default_flow_style=False)
                )
    return cleanup_performed


def build_project_repo(
    project_id: str, runner_responses_for_project: Dict,
    ssh_pkey_file: str, user: str, thread_lock: Lock, log: CBCloudLogger
) -> None:
    try:
        if _set_lock(project_id, thread_lock, log):
            target_path = os.path.normpath(
                os.sep.join([Defaults.get_repo_root(), project_id])
            )
            project_path = os.path.dirname(target_path)
            project_indicator = os.sep.join(
                [project_path, '.project']
            )

            log.info(f'Creating project indicator: {project_indicator!r}')
            Path.wipe(project_indicator)
            Path.create(project_indicator)

            if not os.path.exists(target_path):
                Path.create(target_path)
            sync_files: Dict[str, List[str]] = {}
            for source_ip in runner_responses_for_project.keys():
                for source_spec in runner_responses_for_project[source_ip]:
                    (source_file, project_package_name) = source_spec.split('|')
                    remote_source_file = f'{user}@{source_ip}:{source_file}'
                    repo_meta = _get_repo_path_for_binary(
                        source_file, target_path, log
                    )
                    if repo_meta:
                        _update_project_indicator(
                            indicator_dir=project_indicator,
                            target_name=os.path.basename(target_path),
                            package_name=project_package_name,
                            repo_file=repo_meta.repo_file
                        )
                        if repo_meta.repo_path in sync_files:
                            sync_files[repo_meta.repo_path].append(
                                remote_source_file
                            )
                        else:
                            sync_files[repo_meta.repo_path] = \
                                [remote_source_file]
            for repo_path in sorted(sync_files.keys()):
                if repo_path != 'unknown':
                    sync_call = Command.run(
                        [
                            'rsync', '-av', '-e', 'ssh -i {0} -o {1}'.format(
                                ssh_pkey_file,
                                'StrictHostKeyChecking=accept-new'
                            )
                        ] + sync_files[repo_path] + [
                            repo_path
                        ], raise_on_error=False
                    )
                    if sync_call.output:
                        log.info(sync_call.output)
                    if sync_call.error:
                        log.error(sync_call.error)

            log.info(f'Running cleanup for: {project_path!r}')
            # check if project got deleted from source
            cleanup = cleanup_project_repo(project_path, log)

            # check if packages in project got deleted from source
            if not cleanup:
                cleanup = cleanup_project_repo_packages(project_path, log)

            # check if targets in packages in project got deleted from source
            if not cleanup:
                cleanup = cleanup_project_repo_packages_targets(
                    project_path, log
                )

            if os.path.exists(target_path):
                if repo_meta.repo_type == 'rpm':
                    _create_rpm_repo(target_path, log)
                else:
                    log.error(
                        f'No idea how to create repo for data in: {target_path}'
                    )
            _set_free(project_id, log)
        else:
            log.info(f'Repo sync for {project_id} is locked')
    except Exception:
        _set_free(project_id, log)


def _update_project_indicator(
    indicator_dir: str, target_name: str, package_name: str, repo_file: str
) -> None:
    if not os.path.exists(indicator_dir):
        # Due to a project cleanup in another thread it can happen
        # that the indicator_dir does no longer exist. In this case
        # return early
        return
    files_info = os.sep.join([indicator_dir, 'files'])
    files_data = {}
    if os.path.isfile(files_info):
        with open(files_info) as files:
            files_data = yaml.safe_load(files)
    modified = False
    if not files_data.get(package_name):
        files_data[package_name] = {}
        modified = True

    if not files_data[package_name].get(target_name):
        files_data[package_name][target_name] = []
        modified = True

    if repo_file not in files_data[package_name][target_name]:
        files_data[package_name][target_name].append(repo_file)
        modified = True

    if modified:
        with open(files_info, 'w') as files:
            files.write(yaml.dump(files_data, default_flow_style=False))


def _get_repo_path_for_binary(
    binary_file_name: str, target_path: str, log: CBCloudLogger
) -> repo_metadata:
    repo_path = 'unknown'
    repo_type = 'unknown'
    if binary_file_name.endswith('.src.rpm'):
        repo_path = f'{target_path}/src'
        repo_type = 'rpm'
    elif binary_file_name.endswith('.noarch.rpm'):
        repo_path = f'{target_path}/noarch'
        repo_type = 'rpm'
    elif binary_file_name.endswith('.rpm'):
        arch = binary_file_name.split('.')[-2]
        repo_path = f'{target_path}/{arch}'
        repo_type = 'rpm'
    else:
        log.info(
            f'No idea how to handle {binary_file_name!r}... skipping'
        )
        return repo_metadata(
            repo_type=repo_type,
            repo_path=repo_path,
            repo_file=''
        )
    if not os.path.isdir(repo_path):
        Path.create(repo_path)
    return repo_metadata(
        repo_type=repo_type,
        repo_path=repo_path,
        repo_file=os.sep.join(
            [repo_path, os.path.basename(binary_file_name)]
        )
    )


def _get_repo_type(source_file: str) -> Optional[str]:
    """
    Lookup repo type according to the package extension of
    the given binary file name
    """
    if source_file.endswith('.rpm'):
        return 'rpm'
    return None


def _create_rpm_repo(target_path: str, log: CBCloudLogger) -> None:
    create_repo_call = Command.run(
        ['createrepo_c', target_path], raise_on_error=False
    )
    if create_repo_call.output:
        log.info(create_repo_call.output)
    if create_repo_call.error:
        log.error(create_repo_call.error)
    # TODO: package and repo signing
    # - signing of repomd.xml or alike if not rpm repo
    # - signing of package files via rpmsign


def _set_lock(project_id: str, thread_lock: Lock, log: CBCloudLogger) -> bool:
    """
    Create lock file for the given project path. Returns
    False if lock is already present. During the creation
    of the file based lock a mutex lock is set to ensure
    no other thread interferes with the file lock for the
    project path.

    :param str project_id: unique path name to describe project
    :param Lock lock: Mutex Lock

    :return:
        Bool value indicating if lock is set or not.
        True means lock was set, False means lock was already set

    :rtype: bool
    """
    thread_lock.acquire()
    lock_set_action = False
    lock_file = '/var/lock/{0}.lock'.format(
        project_id.replace(os.sep, '_')
    )
    if os.path.isfile(lock_file):
        lock_set_action = False
    else:
        log.info(f'Set lock {lock_file}')
        with open(lock_file, 'w'):
            pass
        lock_set_action = True
    thread_lock.release()
    return lock_set_action


def _set_free(project_id: str, log: CBCloudLogger) -> None:
    lock_file = '/var/lock/{0}.lock'.format(
        project_id.replace(os.sep, '_')
    )
    log.info(f'Release lock {lock_file}')
    Path.wipe(lock_file)


def _get_datetime_from_utc_timestamp(timestamp: str) -> datetime:
    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
