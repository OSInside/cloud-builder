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
import os
from typing import (
    NamedTuple, List
)

from kiwi.path import Path

status_flags = NamedTuple(
    'status_flags', [
        ('package_rebuild', str),
        ('package_source_rebuild', str),
        ('package_build_failed', str),
        ('package_build_failed_no_binaries', str),
        ('package_binaries_sync_failed', str),
        ('image_build_failed', str),
        ('package_build_succeeded', str),
        ('image_build_succeeded', str),
        ('buildroot_setup_failed', str),
        ('buildroot_setup_succeeded', str),
        ('package_request_accepted', str),
        ('incompatible_build_arch', str),
        ('reset_running_build', str),
        ('project_not_existing', str),
        ('project_metadata_not_existing', str),
        ('package_target_not_configured', str),
        ('image_target_not_configured', str),
        ('image_source_rebuild', str),
        ('image_rebuild', str),
        ('image_request_accepted', str),
        ('invalid_metadata', str),
        ('package_local', str),
        ('image_local', str)
    ]
)


class Defaults:
    """
    Implements Cloud Builder project default values
    """
    @staticmethod
    def get_cloud_builder_meta_project_setup_file_name() -> str:
        """
        Return the basename of the  project setup configuration
        file used to provide information about the target package
        or image
        """
        return 'cloud_builder.yml'

    @staticmethod
    def get_cloud_builder_meta_build_root_file_name() -> str:
        """
        Return the basename of the buildroot kiwi config file
        used to setup the build environment when building
        packages
        """
        return 'build_root.kiwi'

    @staticmethod
    def get_cloud_builder_meta_dir() -> str:
        """
        Return meta data directory which contains the
        cloud builder setup files to build packages and images
        """
        return '.cb'

    @staticmethod
    def get_build_request_queue_name() -> str:
        """
        Return default name of message queue used for sending
        package build requests.

        Queue is a shared queue:
        Each reader compete with each other and for each message,
        only one reader will get it. It's important to configure
        the queue in a way that it distributes requests across
        readers. In kafka this done by assigning as many partitions
        as there are potential readers
        """
        return 'cb-build-request'

    @staticmethod
    def get_response_queue_name() -> str:
        """
        Return name of message queue used for sending
        response messages of the Cloud Builder system

        Queue is a publish/subscribe queue:
        Each message is broadcast to all readers.
        """
        return 'cb-response'

    @staticmethod
    def get_info_request_queue_name() -> str:
        """
        Return name of message queue used for sending
        info requests

        Queue is a publish/subscribe queue:
        Each message is broadcast to all readers.
        """
        return 'cb-info-request'

    @staticmethod
    def get_info_response_queue_name() -> str:
        """
        Return name of message queue used for sending
        info response messages

        Queue is a publish/subscribe queue:
        Each message is broadcast to all readers.
        """
        return 'cb-info-response'

    @staticmethod
    def get_runner_result_paths() -> List[str]:
        """
        Returns a path list below which the used packaging
        tool stores the build results. At the moment this
        method is aligned to the behavior of the build tool
        provided with the open buildservice project.

        :return: directory path list

        :rtype: list
        """
        return ['home/abuild', 'usr/src/packages/DEBS']

    @staticmethod
    def get_package_formats() -> List[str]:
        """
        Return list of package format expressions used in find
        to lookup package results

        :rtype: list
        """
        return [
            '*.rpm', '*.deb'
        ]

    @staticmethod
    def get_cb_logfile() -> str:
        """
        Return local logfile pathname

        :return: file path name

        :rtype: str
        """
        return '/var/log/cloud_builder.log'

    @staticmethod
    def get_runner_root() -> str:
        """
        Return root path name to build packages/images

        :return: directory path name

        :rtype: str
        """
        return '/var/tmp/CB'

    @staticmethod
    def get_repo_root() -> str:
        """
        Return root path to serve repos

        :return: directory path name

        :rtype: str
        """
        return '/srv/www/projects'

    @staticmethod
    def get_status_flags() -> status_flags:
        """
        Return named tuple to represent status information

        :return: A static tuple directory

        :rtype: NamedTuple
        """
        return status_flags(
            package_rebuild='package rebuild requested',
            package_source_rebuild='package rebuild due to source change',
            package_build_failed='package build failed',
            package_build_failed_no_binaries='package build failed, no binaries found',
            package_binaries_sync_failed='package binaries sync failed',
            image_build_failed='image build failed',
            package_build_succeeded='package build succeeded',
            image_build_succeeded='image build succeeded',
            buildroot_setup_failed='build root setup failed',
            buildroot_setup_succeeded='build root setup succeeded',
            package_request_accepted='package request accepted',
            incompatible_build_arch='incompatible build arch',
            reset_running_build='reset running build',
            project_not_existing='project does not exist',
            project_metadata_not_existing='project metadata does not exist',
            invalid_metadata='invalid package metadata',
            package_target_not_configured='package target not configured',
            image_target_not_configured='image target not configured',
            image_source_rebuild='image rebuild due to source change',
            image_rebuild='image rebuild requested',
            image_request_accepted='image request accepted',
            package_local='package build on localhost requested',
            image_local='image build on localhost requested'
        )

    @staticmethod
    def get_runner_project_dir() -> str:
        """
        Checkout path for github project on the runner

        :return: directory path name

        :rtype: str
        """
        return f'{os.environ.get("HOME")}/cloud_builder_sources'

    @staticmethod
    def get_projects_path(package_source: str) -> str:
        """
        Return project path from given package source path

        :return: directory path name

        :rtype: str
        """
        return os.path.dirname(
            package_source.replace(
                Defaults.get_runner_project_dir(), ''
            ).lstrip(os.sep)
        )

    @staticmethod
    def get_broker_config() -> str:
        """
        Location of broker credentials and setup instructions

        :return: A file path

        :rtype: str
        """
        return '/etc/cloud_builder_broker.yml'

    @staticmethod
    def get_cb_ctl_config() -> str:
        """
        Location of control plane (cb-ctl) config file

        :return: A file path

        :rtype: str
        """
        return os.path.join(Defaults.__conf_path(), 'cbctl.yml')

    @staticmethod
    def get_kiwi() -> str:
        """
        Lookup kiwi binary

        :return:
            A file path or the default binary name to run kiwi-ng

        :rtype: str
        """
        for kiwi in ['kiwi-ng', 'kiwi-ng-3']:
            kiwi_path = Path.which(
                kiwi, alternative_lookup_paths=['/usr/local/bin']
            )
            if kiwi_path:
                return kiwi_path
        return 'kiwi-ng'

    @staticmethod
    def __conf_path() -> str:
        """
        Base directory of config files for Cloud Builder

        :return: A directory path

        :rtype: str
        """
        return os.path.join(
            os.environ.get('HOME') or '', '.config/cb'
        )
