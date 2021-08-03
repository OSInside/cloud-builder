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
from typing import NamedTuple

status_flags = NamedTuple(
    'status_flags', [
        ('package_rebuild', str),
        ('package_rebuild_clean', str),
        ('package_source_rebuild', str),
        ('package_source_rebuild_clean', str),
        ('package_build_failed', str),
        ('package_build_succeeded', str),
        ('package_build_running', str),
        ('buildroot_setup_failed', str),
        ('buildroot_setup_succeeded', str),
        ('package_request_accepted', str),
        ('incompatible_build_arch', str),
        ('reset_running_build', str),
        ('package_not_existing', str),
        ('package_metadata_not_existing', str),
        ('package_target_not_configured', str),
        ('invalid_metadata', str)
    ]
)


class Defaults:
    """
    Implements Cloud Builder project default values
    """
    @staticmethod
    def get_cloud_builder_metadata_file_name() -> str:
        """
        Return name of package configuration file to be used
        with Cloud Builder
        """
        return 'cloud_builder.yml'

    @staticmethod
    def get_cloud_builder_kiwi_file_name() -> str:
        """
        Return name of package buildroot kiwi config file to
        be used with Cloud Builder
        """
        return 'cloud_builder.kiwi'

    @staticmethod
    def get_package_request_queue_name() -> str:
        """
        Return name of message queue used for sending
        package build requests.

        Queue is a shared queue:
        Each reader compete with each other and for each message,
        only one reader will get it. It's important to configure
        the queue in a way that it distributes requests across
        readers. In kafka this done by assigning as many partitions
        as there are potential readers
        """
        return 'cb-package-request'

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
    def get_runner_results_root() -> str:
        """
        Returns the root path below which the used packaging
        tool stores the build results. At the moment this
        method is aligned to the behavior of the build tool
        provided with the open buildservice project.

        :return: directory path

        :rtype: str
        """
        return 'home/abuild'

    @staticmethod
    def get_cb_logfile() -> str:
        """
        Return local logfile pathname

        :return: file path name

        :rtype: str
        """
        return '/var/log/cloud_builder.log'

    @staticmethod
    def get_runner_package_root() -> str:
        """
        Return root path name to construct package build roots
        for building the packages on the runner

        :return: directory path name

        :rtype: str
        """
        return '/var/tmp/CB'

    @staticmethod
    def get_status_flags() -> status_flags:
        """
        Return named tuple to represent status information

        :return: A static tuple directory

        :rtype: NamedTuple
        """
        return status_flags(
            package_rebuild='package rebuild requested',
            package_rebuild_clean='package rebuild on new buildroot',
            package_source_rebuild='package rebuild due to source change',
            package_source_rebuild_clean='package rebuild on new buildroot due to source change',
            package_build_failed='package build failed',
            package_build_succeeded='package build succeeded',
            package_build_running='package build running',
            buildroot_setup_failed='build root setup failed',
            buildroot_setup_succeeded='build root setup succeeded',
            package_request_accepted='package request accepted',
            incompatible_build_arch='incompatible build arch',
            reset_running_build='reset running build',
            package_not_existing='package does not exist',
            package_metadata_not_existing='package metadata does not exist',
            invalid_metadata='invalid package metadata',
            package_target_not_configured='package target not configured'
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
    def __conf_path() -> str:
        """
        Base directory of config files for Cloud Builder

        :return: A directory path

        :rtype: str
        """
        return os.path.join(
            os.environ.get('HOME') or '', '.config/cb'
        )
