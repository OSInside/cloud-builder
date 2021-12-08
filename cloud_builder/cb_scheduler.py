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
usage: cb-scheduler -h | --help
       cb-scheduler
           [--update-interval=<time_sec>]
           [--poll-timeout=<time_msec>]
           [--build-limit=<number>]
           [(--repo-server=<name> --ssh-user=<user> --ssh-pkey=<ssh_pkey_file>)]

options:
    --update-interval=<time_sec>
        Optional update interval to reconnect to the
        message broker. Default is 10sec

    --poll-timeout=<time_msec>
        Optional message broker poll timeout to return if no
        requests are available. Default: 5000msec

    --build-limit=<number>
        Max number of build processes this scheduler handles
        at the same time. Default: 10

    --repo-server=<name>
        Name or IP of collector repo server

    --ssh-pkey=<ssh_pkey_file>
        Path to ssh private key file to access repo server

    --ssh-user=<user>
        User name to access repo server
"""
import os
import glob
import platform
import psutil
import signal
from docopt import docopt
from textwrap import dedent
from cloud_builder.utils.git import CBGit
from cloud_builder.version import __version__
from cloud_builder.cloud_logger import CBCloudLogger
from cloud_builder.response.response import CBResponse
from cloud_builder.defaults import Defaults
from cloud_builder.project_metadata.project_metadata import CBProjectMetaData
from cloud_builder.broker import CBMessageBroker
from kiwi.command import Command
from kiwi.privileges import Privileges
from kiwi.path import Path
from apscheduler.schedulers.background import BlockingScheduler
from typing import (
    Dict, List, NamedTuple, Optional
)

from cloud_builder.exceptions import (
    exception_handler,
    CBSchedulerIntervalError
)

request_validation_type = NamedTuple(
    'request_validation_type', [
        ('project_config', Dict),
        ('response', Optional[CBResponse]),
        ('is_valid', bool)
    ]
)

repo_server_type = NamedTuple(
    'repo_server_type', [
        ('host', str),
        ('user', str),
        ('pkey', str)
    ]
)

SCHEDULER_INSTANCES: int = 0


@exception_handler
def main() -> None:
    """
    cb-scheduler - listens on incoming package and image build
    requests from the message broker on a regular schedule.
    Only if the max package/image to build limit is not exceeded,
    request messages from the broker are accepted. In case the request
    matches the runner capabilities e.g architecture it gets
    acknowledged and removed from the broker queue.

    A package can be build for different distribution targets
    and architectures. Each distribution target/arch needs to
    be configured as a profile in the build_root.kiwi metadata and
    added as effective build target in the cloud_builder.yml
    configuration file:

    .cb
     ├── build_root.kiwi
     └── cloud_builder.yml

    An example cloud_builder.yml config to build the xclock package
    for the Tumbleweed distribution for x86_64 and aarch64
    would look like the following:

    .. code:: yaml

        schema_version: 0.1
        name: xclock

        distributions:
          -
            dist: TW
            arch: x86_64
            runner_group: suse

          -
            dist: TW
            arch: aarch64
            runner_group: suse

    The above instructs the scheduler to create two buildroot
    environments, one for Tumbleweed(x86_64) and one for
    Tumbleweed(aarch64) and build the xclock package in each
    of these buildroots. To process this properly the scheduler
    creates a script which calls cb-prepare followed by cb-run
    with the corresponding parameters for each element of the
    distributions list. Each dist.arch build process is triggered
    by one build request. In the above example two requests
    to build all targets in the distributions list would be
    required.

    The dist and arch settings of a distribution are combined
    into profile names given to cb-prepare as parameter and used
    in KIWI to create the buildroot environment. From the above
    example this would lead to two profiles named:

    * TW.x86_64
    * TW.aarch64

    The build_root.kiwi metadata file has to provide instructions
    such that the creation of a correct buildroot for these
    profiles is possible.

    --

    An image can be build for different profiles, build arguments
    and architectures. In contrast to a package build the image
    build only requires the cloud_builder.yml configuration file:

    .cb
     └── cloud_builder.yml

    An example image config to build myimage for myprofile and
    for the x86_64 achitecture would look like the following:

    .. code:: yaml

        schema_version: 0.1
        name: myimage

        images:
          -
            arch: x86_64
            runner_group: suse
            selection:
              name: standard
              profiles:
                - myprofile
              build_arguments:
                - "--clear-cache"

    The above instructs the scheduler to build one image for the
    myprofile profile and the x86_64 achitecture on a runner in the
    suse group. The package cache on this runner will be cleared
    prior building the image. The image output files will be packaged
    into an rpm package. To do this properly the scheduler creates a
    script which calls cb-image.

    The project directory is treated as the image description directory
    and passed as such to the KIWI image builder via cb-image.
    KIWI searches for a *.kiwi or config.xml file to accept the
    directory as an image description. If the cloud builder configuration
    file cloud_builder.yml names a profile, that profile must be
    defined in the KIWI config file.
    """
    args = docopt(
        __doc__,
        version='CB (scheduler) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()

    log = CBCloudLogger('CBScheduler', '(system)')
    log.set_logfile()

    Path.create(
        Defaults.get_runner_root()
    )
    Path.create(
        os.path.join(Defaults.get_runner_root(), 'scheduled')
    )

    running_limit = int(args['--build-limit'] or 10)
    update_interval = int(args['--update-interval'] or 10)
    poll_timeout = int(args['--poll-timeout'] or 5000)

    repo_server = repo_server_type(
        host=args['--repo-server'] or 'none',
        user=args['--ssh-user'] or 'none',
        pkey=args['--ssh-pkey'] or 'none'
    )

    if poll_timeout / 1000 > update_interval:
        # This should not be allowed, as the BlockingScheduler would
        # just create unnneded threads and new consumers which could
        # cause an expensive rebalance on the message broker
        raise CBSchedulerIntervalError(
            'Poll timeout on the message broker greater than update interval'
        )

    handle_build_requests(poll_timeout, running_limit, repo_server, log)

    project_scheduler = BlockingScheduler()
    project_scheduler.add_job(
        lambda: handle_build_requests(
            poll_timeout, running_limit, repo_server, log
        ), 'interval', seconds=update_interval
    )
    project_scheduler.start()


def handle_build_requests(
    poll_timeout: int, running_limit: int,
    repo_server: repo_server_type, log: CBCloudLogger
) -> None:
    """
    Check on the runner state and if ok listen to the
    message broker queue for new package/image build requests
    The build_request_queue is used as shared queue
    within a single group. It's important to have this
    queue configured to distribute messages across
    several readers to let multiple CB scheduler scale

    :param int poll_timeout:
        timeout in msec after which the blocking read() to the
        message broker returns
    :param int running_limit:
        allow up to running_limit package builds at the same time.
        If exceeded an eventual connection to the message broker
        will be closed and opened again if the limit is no
        longer reached
    """
    global SCHEDULER_INSTANCES
    if SCHEDULER_INSTANCES != 0:
        log.info('Scheduler already running')
        return

    if get_running_builds() >= running_limit:
        # runner is busy...
        log.info('Max running builds limit reached')
        return

    broker = CBMessageBroker.new(
        'kafka', config_file=Defaults.get_broker_config()
    )
    SCHEDULER_INSTANCES += 1
    try:
        while(True):
            if get_running_builds() >= running_limit:
                # runner is busy...
                log.info('Max running builds limit reached')
                break
            for message in broker.read(
                topic=broker.get_runner_group(), timeout_ms=poll_timeout
            ):
                request = broker.validate_build_request(message.value)
                if request:
                    project_source_path = os.path.join(
                        Defaults.get_runner_project_dir(),
                        format(request['project'])
                    )
                    update_source_repo(request, log)
                    validated_request = is_request_valid(
                        project_source_path, request, log
                    )
                    if validated_request.is_valid:
                        broker.acknowledge()

                    if validated_request.response:
                        log.response(validated_request.response, broker)

                    build_config = validated_request.project_config

                    if build_config and 'distributions' in build_config:
                        build_package(
                            request, broker, repo_server, log
                        )
                    elif build_config and 'images' in build_config:
                        build_image(
                            request, build_config, broker, repo_server, log
                        )
    finally:
        log.info('Closing message broker connection')
        SCHEDULER_INSTANCES -= 1
        broker.close()


def update_source_repo(request: Dict, log: CBCloudLogger) -> None:
    status_flags = Defaults.get_status_flags()
    if request['action'] == status_flags.package_rebuild or \
       request['action'] == status_flags.package_source_rebuild or \
       request['action'] == status_flags.image_rebuild or \
       request['action'] == status_flags.image_source_rebuild:
        log.info('Update project git source repo prior build')
        CBGit(checkout_path=Defaults.get_runner_project_dir()).pull()


def build_image(
    request: Dict, build_config: Dict, broker: CBMessageBroker,
    repo_server: repo_server_type, log: CBCloudLogger
) -> None:
    """
    Update the image sources and run the script which
    utilizes cb-image to build the image for the requested
    target

    :param dict request: yaml dict request record
    :param dict build_config: yaml dict project configuration
    :param CBMessageBroker broker: instance of CBMessageBroker
    """
    log.set_id(os.path.basename(request['project']))
    reset_build_if_running(
        request, log, broker
    )
    log.info('Starting image build process')
    Command.run(
        [
            'bash', create_image_run_script(
                request, build_config, repo_server=repo_server
            )
        ]
    )


def build_package(
    request: Dict, broker: CBMessageBroker,
    repo_server: repo_server_type, log: CBCloudLogger
) -> None:
    """
    Update the package sources and run the script which
    utilizes cb-prepare/cb-run to build the package for
    the requested target

    :param dict request: yaml dict request record
    :param CBMessageBroker broker: instance of CBMessageBroker
    """
    log.set_id(os.path.basename(request['project']))
    reset_build_if_running(
        request, log, broker
    )
    log.info('Starting package build process')
    Command.run(
        [
            'bash', create_package_run_script(
                request, repo_server=repo_server
            )
        ]
    )


def reset_build_if_running(
    request: Dict, log: CBCloudLogger, broker: CBMessageBroker
) -> None:
    """
    Check if the same package/arch is currently/still running
    and kill the process associated with it

    :param dict request: yaml dict request record
    :param CBCloudLogger log: logger instance
    :param CBMessageBroker broker: instance of CBMessageBroker
    """
    build_pid = 0
    status_flags = Defaults.get_status_flags()
    response = CBResponse(request['request_id'], log.get_id())
    project_root = os.path.join(
        Defaults.get_runner_root(), request['project']
    )
    if 'package' in request:
        dist_profile = \
            f'{request["package"]["dist"]}.{request["package"]["arch"]}'
        build_root = f'{project_root}@{dist_profile}'
        build_pid = is_active(f'{build_root}.pid', log)
        if build_pid:
            response.set_package_jobs_reset_response(
                message='Kill job group for PID:{0} prior rebuild'.format(
                    build_pid
                ),
                response_code=status_flags.reset_running_build,
                package=request['project'],
                arch=request['package']['arch'],
                dist=request['package']['dist']
            )
    elif 'image' in request:
        selection = \
            f'{request["image"]["selection"]}.{request["image"]["arch"]}'
        image_root = f'{project_root}@{selection}'
        build_pid = is_active(f'{image_root}.pid', log)
        if build_pid:
            response.set_image_jobs_reset_response(
                message='Kill job group for PID:{0} prior rebuild'.format(
                    build_pid
                ),
                response_code=status_flags.reset_running_build,
                image=request['project'],
                arch=request['image']['arch'],
                selection=request['image']['selection']
            )
    if build_pid:
        log.response(response, broker)
        os.kill(build_pid, signal.SIGTERM)


def get_running_builds() -> int:
    """
    Lookup the process table for running builds

    :return: Number of running build processes

    :rtype: int
    """
    runnung_builds = 0
    build_pids = os.path.join(
        Defaults.get_runner_root(), 'scheduled'
    )
    for pid_file in sorted(glob.iglob(f'{build_pids}/*.pid')):
        with open(pid_file) as pid_fd:
            build_pid = int(pid_fd.read().strip())
            if psutil.pid_exists(build_pid):
                runnung_builds += 1
    return runnung_builds


def is_request_valid(
    project_source_path: str, request: Dict, log: CBCloudLogger = None
) -> request_validation_type:
    """
    Sanity checks between the request and the package sources

    1. Check if given package/image source exists
    2. Check if there is a cloud builder metadata and a .kiwi file
    3. Check if architecture + runner_group is configured in the metadata
    4. Check if dist is configured for package builds
    5. Check if the host architecture is compatbile with the
       request architecture

    :param str project_source_path: path to package/image sources
    :param dict request: yaml dict request record

    :return: request_validation_type

    :rtype: tuple
    """
    status_flags = Defaults.get_status_flags()
    response = CBResponse(
        request['request_id'], log.get_id() if log else 'local'
    )
    # 1. Check on project sources to exist
    if not os.path.isdir(project_source_path):
        response.set_project_not_existing_response(
            message=f'Project does not exist: {project_source_path}',
            response_code=status_flags.project_not_existing,
            project=request['project']
        )
        return request_validation_type(
            project_config={},
            response=response,
            is_valid=False
        )

    # 2. Check on project metadata to exist
    project_metadata = os.path.join(
        project_source_path, Defaults.get_cloud_builder_meta_dir(),
        Defaults.get_cloud_builder_meta_project_setup_file_name()
    )
    if not os.path.isfile(project_metadata):
        response.set_project_metadata_not_existing_response(
            message=f'Project metadata does not exist: {project_metadata}',
            response_code=status_flags.project_metadata_not_existing,
            project=request['project']
        )
        return request_validation_type(
            project_config={},
            response=response,
            is_valid=False
        )

    # 3. Check if requested package arch+dist+runner_group is configured
    project_config = CBProjectMetaData.get_project_config(
        project_source_path, log, request['request_id']
    )
    if not project_config:
        return request_validation_type(
            project_config={},
            response=None,
            is_valid=False
        )
    request_arch = 'none'
    request_dist = 'none'
    request_selection = 'none'
    if 'package' in request:
        target_ok = False
        request_arch = request['package']['arch']
        request_dist = request['package']['dist']
        request_runner_group = request['runner_group']
        for target in project_config.get('distributions') or []:
            allowed_runner_groups = [target.get('runner_group'), 'local']
            if request_arch == target.get('arch') and \
               request_dist == target.get('dist') and \
               request_runner_group in allowed_runner_groups:
                target_ok = True
                break
        if not target_ok:
            response.set_project_invalid_target_response(
                message='No {0} config for: {1}.{2} in runner group {3}'.format(
                    'package', request_dist, request_arch, request_runner_group
                ),
                response_code=status_flags.package_target_not_configured,
                project=request['project']
            )
            return request_validation_type(
                project_config={},
                response=response,
                is_valid=False
            )

    # 4. Check if requested image arch+runner_group+selection is configured
    if 'image' in request:
        target_ok = False
        request_arch = request['image']['arch']
        request_selection = request['image']['selection']
        request_runner_group = request['runner_group']
        for target in project_config.get('images') or []:
            allowed_runner_groups = [target.get('runner_group'), 'local']
            if request_arch == target.get('arch') and \
               request_selection == target.get('selection').get('name') and \
               request_runner_group in allowed_runner_groups:
                target_ok = True
                break
        if not target_ok:
            response.set_project_invalid_target_response(
                message='No {0} config for: {1}.{2} in runner group {3}'.format(
                    'image', request_selection, request_arch,
                    request_runner_group
                ),
                response_code=status_flags.image_target_not_configured,
                project=request['project']
            )
            return request_validation_type(
                project_config={},
                response=response,
                is_valid=False
            )

    # 5. Check if host architecture is compatbile
    if request_arch and request_arch != platform.machine():
        response.set_buildhost_arch_incompatible_response(
            message=f'Incompatible arch: {platform.machine()}',
            response_code=status_flags.incompatible_build_arch,
            package=request['project']
        )
        return request_validation_type(
            project_config={},
            response=response,
            is_valid=False
        )

    # All good...
    if 'package' in request:
        response.set_package_build_scheduled_response(
            message='Accept package build request',
            response_code=status_flags.package_request_accepted,
            package=request['project'],
            arch=request_arch,
            dist=request_dist
        )
    elif 'image' in request:
        response.set_image_build_scheduled_response(
            message='Accept image build request',
            response_code=status_flags.image_request_accepted,
            image=request['project'],
            arch=request_arch,
            selection=request_selection
        )
    return request_validation_type(
        project_config=project_config,
        response=response,
        is_valid=True
    )


def create_image_run_script(
    request: Dict, build_config: Dict,
    bundle_id: str = '0', local_build: bool = False,
    repo_server: repo_server_type = repo_server_type(
        host='none', user='none', pkey='none'
    )
) -> str:
    """
    Create script to call cb-image

    :param dict request: yaml dict request record
    :param dict build_config: yaml dict project configuration
    :param str bundle_id: optional package bundle ID, defaults to '0'
    :param bool local_build:
        create script for build on localhost. This keeps
        the script in the foreground and prints all information
        to stdout instead of writing log files

    :return: script file path name

    :rtype: str
    """
    build_options: List[str] = []
    profiles: List[str] = []
    for target in build_config.get('images') or []:
        selection = target['selection']
        if selection['name'] == request['image']['selection']:
            build_options = selection.get('build_arguments') or []
            profiles = selection.get('profiles') or []

    profile_opts = []
    for profile in profiles:
        profile_opts.extend(['--profile', profile])

    selection = request['image']['selection']

    custom_args = ['--']
    for argument in build_options:
        custom_args.append(argument)

    if local_build:
        image_source_path = request['project']
        image_target_path = \
            f'{image_source_path}@{selection}.{request["image"]["arch"]}'

        run_script = dedent('''
            #!/bin/bash
            set -e
            rm -rf {image_target_path}
            cb-image \\
                --request-id {request_id} \\
                --bundle-id {bundle_id} \\
                --description {image_source_path} \\
                --target-dir {image_target_path} \\
                --local \\
                {profile_opts} {custom_args}
        ''').format(
            image_source_path=image_source_path,
            image_target_path=image_target_path,
            profile_opts=' '.join(profile_opts) if profile_opts else '',
            custom_args=' '.join(custom_args) if build_options else '',
            request_id=request['request_id'],
            bundle_id=bundle_id
        )
    else:
        repo_path = os.sep.join(
            [os.path.dirname(request['project']), selection]
        )
        repo_arch = request['image']['arch']
        image_source_path = os.path.join(
            Defaults.get_runner_project_dir(), request['project']
        )
        build_pid_file = '{0}/{1}@{2}.{3}'.format(
            os.path.join(Defaults.get_runner_root(), 'scheduled'),
            os.path.basename(request['project']),
            selection, request['image']['arch'] + '.pid'
        )
        image_target_path = '{0}@{1}.{2}'.format(
            os.path.join(Defaults.get_runner_root(), request['project']),
            selection, request['image']['arch']
        )
        run_script = dedent('''
            #!/bin/bash
            set -e

            rm -rf {image_target_path}

            function finish {{
                kill $(jobs -p) &>/dev/null
            }}

            {{
                trap finish EXIT
                cb-image \\
                    --request-id {request_id} \\
                    --bundle-id {bundle_id} \\
                    --description {image_source_path} \\
                    --target-dir {image_target_path} \\
                    --repo-path {repo_path} \\
                    --repo-arch {repo_arch} \\
                    --repo-server {repo_server} \\
                    --ssh-user {ssh_user} \\
                    --ssh-pkey {ssh_pkey} \\
                    {profile_opts} {custom_args}
            }} &>>{image_target_path}.run.log &

            echo $! > {image_target_path}.pid
            echo $! > {build_pid_file}
        ''').format(
            image_source_path=image_source_path,
            image_target_path=image_target_path,
            profile_opts=' '.join(profile_opts) if profile_opts else '',
            custom_args=' '.join(custom_args) if build_options else '',
            request_id=request['request_id'],
            repo_path=repo_path,
            repo_arch=repo_arch,
            repo_server=repo_server.host,
            ssh_user=repo_server.user,
            ssh_pkey=repo_server.pkey,
            bundle_id=bundle_id,
            build_pid_file=build_pid_file
        )
    image_run_script = f'{image_target_path}.sh'
    Path.create(os.path.dirname(image_run_script))
    with open(image_run_script, 'w') as script:
        script.write(run_script)
    return image_run_script


def create_package_run_script(
    request: Dict, buildroot_rebuild: bool = True, local_build: bool = False,
    repo_server: repo_server_type = repo_server_type(
        host='none', user='none', pkey='none'
    )
) -> str:
    """
    Create script to call cb-prepare followed by cb-run
    for each configured distribution/arch

    :param dict request: yaml dict request record
    :param bool buildroot_rebuild: rebuild buildroot True|False
    :param bool local_build:
        create script for build on localhost. This keeps
        the script in the foreground and prints all information
        to stdout instead of writing log files

    :return: file path name for script

    :rtype: str
    """
    dist_profile = f'{request["package"]["dist"]}.{request["package"]["arch"]}'
    if local_build:
        package_source_path = request['project']
        package_root = package_source_path
        build_root = f'{package_root}@{dist_profile}'
        run_script = dedent('''
            #!/bin/bash

            set -e

            if {buildroot_rebuild}; then
                rm -rf {build_root}
            fi

            cb-prepare --root {build_root} \\
                --package {package_source_path} \\
                --profile {dist_profile} \\
                --request-id {request_id} \\
                --local
            cb-run --root {build_root} \\
                --request-id {request_id} \\
                --local
        ''').format(
            buildroot_rebuild='true' if buildroot_rebuild else 'false',
            package_source_path=package_source_path,
            dist_profile=dist_profile,
            build_root=build_root,
            request_id=request['request_id']
        )
    else:
        repo_path = os.sep.join(
            [os.path.dirname(request['project']), request['package']['dist']]
        )
        repo_arch = request['package']['arch']
        package_source_path = os.path.join(
            Defaults.get_runner_project_dir(), request['project']
        )
        build_pid_file = '{0}/{1}@{2}'.format(
            os.path.join(Defaults.get_runner_root(), 'scheduled'),
            os.path.basename(request['project']), dist_profile + '.pid'
        )
        package_root = os.path.join(
            Defaults.get_runner_root(), request['project']
        )
        build_root = f'{package_root}@{dist_profile}'
        run_script = dedent('''
            #!/bin/bash

            set -e

            rm -f {build_root}.log

            touch {build_root}.build.log

            function finish {{
                kill $(jobs -p) &>/dev/null
            }}

            {{
                trap finish EXIT
                cb-prepare --root {build_root} \\
                    --package {package_source_path} \\
                    --profile {dist_profile} \\
                    --request-id {request_id}
                cb-run --root {build_root} &> {build_root}.build.log \\
                    --request-id {request_id} \\
                    --repo-path {repo_path} \\
                    --repo-arch {repo_arch} \\
                    --repo-server {repo_server} \\
                    --ssh-user {ssh_user} \\
                    --ssh-pkey {ssh_pkey} \\
                    --clean
            }} &>>{build_root}.run.log &

            echo $! > {build_root}.pid
            echo $! > {build_pid_file}
        ''').format(
            package_source_path=package_source_path,
            dist_profile=dist_profile,
            build_root=build_root,
            request_id=request['request_id'],
            repo_path=repo_path,
            repo_arch=repo_arch,
            repo_server=repo_server.host,
            ssh_user=repo_server.user,
            ssh_pkey=repo_server.pkey,
            build_pid_file=build_pid_file
        )
    package_run_script = f'{build_root}.sh'
    Path.create(os.path.dirname(package_run_script))
    with open(package_run_script, 'w') as script:
        script.write(run_script)
    return package_run_script


def is_active(pid_file: str, log: CBCloudLogger) -> int:
    if os.path.isfile(pid_file):
        with open(pid_file) as pid_fd:
            build_pid = int(pid_fd.read().strip())
        log.info(
            'Checking state of former build with PID:{0}'.format(
                build_pid
            )
        )
        if psutil.pid_exists(build_pid):
            return build_pid
    return 0
