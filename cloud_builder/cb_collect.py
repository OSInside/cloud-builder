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
       cb-collect --project=<github_project>
           [--branch=<name>]
           [--update-interval=<time_sec>]

options:
    --project=<github_project>
        git clone source URI to fetch project with
        packages managed to build in cloud builder

    --branch=<name>
        git branch name

    --update-interval=<time_sec>
        Update interval to ask for new packages/images
        Default: 30sec
"""
import logging
import re
import os
import time
import yaml
from threading import (
    Thread, Lock
)
from docopt import docopt
from cloud_builder.utils.git import CBGit
from cloud_builder.version import __version__
from cloud_builder.cloud_logger import CBCloudLogger
from cloud_builder.identity import CBIdentity
from cloud_builder.exceptions import exception_handler
from cloud_builder.defaults import Defaults
from cloud_builder.project_metadata.project_metadata import CBProjectMetaData
from kiwi.command import Command
from kiwi.logger import Logger
from kiwi.privileges import Privileges
from kiwi.path import Path
from typing import (
    Dict, List, NamedTuple, Optional
)

repo_type = NamedTuple(
    'repo_type', [
        ('name', str),
        ('update_flag', bool)
    ]
)

REPO_LOCK: Dict[str, bool] = {}


@exception_handler
def main() -> None:
    """
    cb-collect - fetches/updates a git repository and
    collects build results of packages and images as they
    are synced here from the runners. Each project in the git
    tree will be represented as a package repository.

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

    git = CBGit(
        args['--project'], Defaults.get_runner_project_dir()
    )
    git.clone(args['--branch'] or '')

    build_repos(
        int(args['--update-interval'] or 30), git, log
    )


def update_project(git: CBGit) -> None:
    """
    Update git repository, fetching latest changes
    """
    git.pull()


def build_repos(update_interval: int, git: CBGit, log: CBCloudLogger) -> None:
    """
    Application loop - building project repositories

    :param int update_interval:
        Wait update_interval seconds before next round
    """
    thread_lock = Lock()

    while(True):
        update_project(git)

        project_target_paths = []
        for root, dirs, files in os.walk(Defaults.get_repo_root()):
            for entry in files:
                if entry.startswith('.package_'):
                    if root not in project_target_paths:
                        project_target_paths.append(root)

        for project_target_path in project_target_paths:
            project_repo_thread = Thread(
                target=build_project_repo,
                args=(
                    os.path.dirname(project_target_path),
                    os.path.basename(project_target_path),
                    thread_lock,
                    log
                )
            )
            project_repo_thread.start()

        # wait update_interval seconds before next round
        time.sleep(update_interval)


def build_project_repo(
    project_path: str, target_name: str, thread_lock: Lock,
    log: CBCloudLogger
) -> None:
    """
    Thread method running for each project and target
    """
    try:
        thread_lock.acquire()
        if not repo_lock_set(project_path, target_name):
            # this repo is already locked
            return
        if thread_lock.locked():
            thread_lock.release()

        repo_type = get_repo_type(
            project_path, target_name, log, unlink_flag=True
        )

        # build project meta needed for cleanup
        create_source_git_meta(
            project_path, target_name
        )

        # 1. check if project got deleted from source
        cleanup = cleanup_project_repo(project_path, log)

        # 2. check if packages in project got deleted from source
        if not cleanup:
            cleanup = cleanup_project_repo_packages(
                project_path, target_name, log
            )

        # 3. check if targets in packages in project got deleted from source
        if not cleanup:
            cleanup = cleanup_project_repo_packages_targets(
                project_path, target_name, log
            )

        # 4. check if arch from targets in packages in project got deleted from source
        if not cleanup:
            cleanup = cleanup_project_repo_packages_target_archs(
                project_path, target_name, log
            )

        # build repo metadata
        if repo_type and (repo_type.update_flag or cleanup):
            create_repo_metadata(
                repo_type.name, project_path, target_name, log
            )
            sign_repo_and_packages(
                repo_type.name, project_path, target_name, log
            )
        repo_lock_release(project_path, target_name)
    except Exception as issue:
        repo_lock_release(project_path, target_name)
        log.error(format(issue))
    finally:
        if thread_lock.locked():
            thread_lock.release()


def repo_lock_set(project_path: str, target_name: str) -> bool:
    """
    Set lock for target in project path

    :param str project_path: Path to the project repo
    :param str target_name:
        Distribution or Selection name as configured
        in the project's cloud_builder.yml

    :return: True if lock can be set, False if already locked

    :rtype: bool
    """
    global REPO_LOCK
    repo_path = os.path.join(
        project_path, target_name
    )
    is_locked = bool(REPO_LOCK.get(repo_path))
    if is_locked:
        return False
    REPO_LOCK[repo_path] = True
    return True


def repo_lock_release(project_path: str, target_name: str) -> None:
    """
    Release lock for target in project path

    :param str project_path: Path to the project repo
    :param str target_name:
        Distribution or Selection name as configured
        in the project's cloud_builder.yml
    """
    global REPO_LOCK
    repo_path = os.path.join(
        project_path, target_name
    )
    if REPO_LOCK.get(repo_path):
        REPO_LOCK[repo_path] = False


def create_source_git_meta(
    project_path: str, target_name: str
) -> str:
    """
    Create source .project source meta file

    The file is used to compare the git source tree with the available
    package/repo results. The information is needed to cleanup the tree
    in case the source repo has deleted projects or package/image
    sources from projects or package/image configurations

    :param str project_path: Path to the project repo
    :param str target_name:
        Distribution or Selection name as configured
        in the project's cloud_builder.yml
    """
    repo_path = os.path.join(
        project_path, target_name
    )
    repo_project = os.path.join(
        repo_path, '.project'
    )
    repo_files = os.path.join(
        repo_project, 'files'
    )
    if not os.path.exists(repo_project):
        Path.create(repo_project)
    repo_project_data: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
    for root, dirs, files in os.walk(repo_path):
        for entry in files:
            repo_file = os.path.join(root, entry)
            repo_file_basename = os.path.basename(repo_file)
            if repo_file_basename.startswith('.package_'):
                package_indicator_format = re.match(
                    r'\.package_([^\.]*)\.(.*)', repo_file_basename
                )
                if package_indicator_format:
                    package_arch = package_indicator_format.group(1)
                    package_name = package_indicator_format.group(2)
                    binary_files = []
                    with open(repo_file) as package_meta:
                        for binary_file in yaml.safe_load(package_meta):
                            binary_files.append(
                                f'{repo_path}/{binary_file.split(".binaries/")[1]}'
                            )
                        binary_files.append(repo_file)
                        if package_name not in repo_project_data:
                            repo_project_data[package_name] = {}
                        if target_name not in repo_project_data[package_name]:
                            repo_project_data[package_name][target_name] = {}
                        if package_arch not in repo_project_data[
                            package_name
                        ][target_name]:
                            repo_project_data[
                                package_name
                            ][target_name][package_arch] = []
                        repo_project_data[
                            package_name
                        ][target_name][package_arch].extend(binary_files)

    if repo_project_data:
        with open(repo_files, 'w') as files_handle:
            files_handle.write(
                yaml.dump(repo_project_data, default_flow_style=False)
            )
    return repo_files


def get_repo_type(
    project_path: str, target_name: str, log: CBCloudLogger,
    unlink_flag: bool = False
) -> Optional[repo_type]:
    """
    Return a repo_type variable containing the repository
    type. The .updaterepo indicator file as provided by
    the runners when they sync their results is primarily
    used to read the repotype from. Once a repo was created
    the .updaterepo indicator will be deleted such that
    the repo metadata is only recreated on new packages from
    runners or on cleanup due to changes in the sources.
    In this case another indicator must be used to detect
    the repotype. For rpm based repos this is the presence
    of the repodata directory. Other repotypes needs to be
    added as we go forward.

    :param str project_path: Path to the project repo
    :param str target_name:
        Distribution or Selection name as configured
        in the project's cloud_builder.yml
    :param CBCloudLogger log:
        log object
    :param bool unlink_flag:
        Delete update repo indicator

    :return:
        repo type name and the information if the repo type
        was detected through the .updaterepo indicator or not

    :rtype: repo_type or None
    """
    repo_path = os.path.join(
        project_path, target_name
    )
    update_repo_file = os.path.join(repo_path, '.updaterepo')
    rpm_repo_indicator = os.path.join(repo_path, 'repodata')
    if os.path.exists(update_repo_file):
        with open(update_repo_file) as flag:
            repo_type_name = flag.read().strip()
        if repo_type_name == 'unknown':
            log.warning(
                f'Repo type unknown for {repo_path!r}'
            )
            return None
        if unlink_flag:
            os.unlink(update_repo_file)
        return repo_type(
            name=repo_type_name,
            update_flag=True
        )
    elif os.path.exists(rpm_repo_indicator):
        return repo_type(
            name='rpm',
            update_flag=False
        )
    else:
        log.warning(
            f'No repo indicator found for {repo_path!r}'
        )
    return None


def create_repo_metadata(
    repo_type: str, project_path: str, target_name: str, log: CBCloudLogger
) -> None:
    """
    Run the method to create repo metadata for the requested repo type

    :param str repo_type: name of repository type
    :param str project_path: Path to the project repo
    :param str target_name:
        Distribution or Selection name as configured
        in the project's cloud_builder.yml
    :param CBCloudLogger log:
        log object
    """
    repo_path = os.path.join(
        project_path, target_name
    )
    if repo_type == 'rpm':
        create_rpm_repo(repo_path, log)


def create_rpm_repo(repo_path: str, log: CBCloudLogger) -> None:
    """
    Create RPM repo

    :param str repo_path: Path to repository
    :param CBCloudLogger log: log object
    """
    log.info(f'Creating repo for {repo_path!r}')
    create_repo_call = Command.run(
        ['createrepo_c', repo_path], raise_on_error=False
    )
    if create_repo_call.output:
        log.info(create_repo_call.output)
    if create_repo_call.error:
        log.error(create_repo_call.error)


def sign_repo_and_packages(
    repo_type: str, project_path: str, target_name: str, log: CBCloudLogger
) -> None:
    # Tracked in: https://github.com/OSInside/cloud-builder/issues/5
    pass


def cleanup_project_repo(project_path: str, log: CBCloudLogger) -> bool:
    """
    Delete project from repos if it was deleted from the git source

    :param str project_path: Path to the project repo
    :param str target_name:
        Distribution or Selection name as configured
        in the project's cloud_builder.yml
    :param CBCloudLogger log: logger
    """
    cleanup_performed = False
    if os.path.exists(project_path):
        source_project = project_path.replace(
            Defaults.get_repo_root(), Defaults.get_runner_project_dir()
        )
        if not os.path.exists(source_project):
            log.info(f'Deleting repos for project {project_path!r}')
            Path.wipe(project_path)
            cleanup_performed = True
    return cleanup_performed


def cleanup_project_repo_packages(
    project_path: str, target_name: str, log: CBCloudLogger
) -> bool:
    """
    Delete packages from project repo if they were deleted
    from the git source

    :param str project_path: Path to the project repo
    :param str target_name:
        Distribution or Selection name as configured
        in the project's cloud_builder.yml
    :param CBCloudLogger log: logger
    """
    repo_path = os.path.join(
        project_path, target_name
    )
    cleanup_performed = False
    project_files_name = f'{repo_path}/.project/files'
    if os.path.isfile(project_files_name):
        with open(project_files_name) as files_handle:
            project_files = yaml.safe_load(files_handle)
        source_project = project_path.replace(
            Defaults.get_repo_root(), Defaults.get_runner_project_dir()
        )
        new_project_files = {}
        for package in project_files.keys():
            package_path = f'{source_project}/{package}'
            if not os.path.exists(package_path):
                log.info(f'Deleting {package!r} from repos')
                for target in project_files[package]:
                    for arch in project_files[package][target]:
                        for file_path in project_files[package][target][arch]:
                            if os.path.isfile(file_path):
                                log.info(f'--> Deleting {file_path!r}')
                                os.unlink(file_path)
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
    project_path: str, target_name: str, log: CBCloudLogger
) -> bool:
    """
    Delete packages from project repo that belongs to specific
    targets (dist or selection) if they were deleted from
    the git source metadata configuration

    :param str project_path: Path to the project repo
    :param str target_name:
        Distribution or Selection name as configured
        in the project's cloud_builder.yml
    :param CBCloudLogger log: logger
    """
    repo_path = os.path.join(
        project_path, target_name
    )
    cleanup_performed = False
    project_files_name = f'{repo_path}/.project/files'
    if os.path.isfile(project_files_name):
        with open(project_files_name) as files_handle:
            project_files = yaml.safe_load(files_handle)
        source_project = project_path.replace(
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
                            f'Deleting {package!r} for {target} from repos'
                        )
                        for arch in project_files[package][target]:
                            for file_path in project_files[package][target][arch]:
                                if os.path.isfile(file_path):
                                    log.info(f'--> Deleting {file_path!r}')
                                    os.unlink(file_path)
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


def cleanup_project_repo_packages_target_archs(
    project_path: str, target_name: str, log: CBCloudLogger
) -> bool:
    """
    Delete packages from project repo that belongs to specific
    target archs if they were deleted from the git source
    metadata configuration

    :param str project_path: Path to the project repo
    :param str target_name:
        Distribution or Selection name as configured
        in the project's cloud_builder.yml
    :param CBCloudLogger log: logger
    """
    repo_path = os.path.join(
        project_path, target_name
    )
    cleanup_performed = False
    project_files_name = f'{repo_path}/.project/files'
    if os.path.isfile(project_files_name):
        with open(project_files_name) as files_handle:
            project_files = yaml.safe_load(files_handle)
        source_project = project_path.replace(
            Defaults.get_repo_root(), Defaults.get_runner_project_dir()
        )
        new_project_files: Dict[str, Dict[str, Dict[str, List]]] = {}
        for package in project_files.keys():
            package_path = f'{source_project}/{package}'
            if os.path.exists(package_path):
                project_config = CBProjectMetaData.get_project_config(
                    package_path, log, CBIdentity.get_request_id()
                )
                target_names = []
                target_archs = []
                if project_config:
                    for target in project_config.get('distributions') or []:
                        target_names.append(target['dist'])
                        target_archs.append(target['arch'])
                    for target in project_config.get('images') or []:
                        target_names.append(target['selection']['name'])
                        target_archs.append(target['arch'])
                for target in project_files[package]:
                    for arch in project_files[package][target]:
                        if arch not in target_archs:
                            log.info(
                                f'Deleting {package!r} for {target}:{arch} from repos'
                            )
                            for file_path in project_files[package][target][arch]:
                                if os.path.isfile(file_path):
                                    log.info(f'--> Deleting {file_path!r}')
                                    os.unlink(file_path)
                                    cleanup_performed = True
                        else:
                            if package not in new_project_files:
                                new_project_files[package] = {}
                            if target not in new_project_files[package]:
                                new_project_files[package][target] = {}
                            new_project_files[package][target][arch] = \
                                project_files[package][target][arch]

        if cleanup_performed:
            with open(project_files_name, 'w') as files_handle:
                files_handle.write(
                    yaml.dump(new_project_files, default_flow_style=False)
                )
    return cleanup_performed
