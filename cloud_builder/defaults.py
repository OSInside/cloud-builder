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
import yaml
from typing import (
    Dict, NamedTuple
)

status_flags = NamedTuple(
    'status_flags', [
        ('package_changed', str),
        ('package_build_failed', str),
        ('package_build_succeeded', str),
        ('buildroot_setup_failed', str),
        ('buildroot_setup_succeeded', str)
    ]
)


class Defaults:
    """
    Implements Cloud Builder project default values
    """
    @staticmethod
    def get_cb_logfile() -> str:
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
            package_changed='package source changed',
            package_build_failed='package build failed',
            package_build_succeeded='package build succeeded',
            buildroot_setup_failed='build root setup failed',
            buildroot_setup_succeeded='build root setup succeeded'
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
    def get_package_config(package_path: str, filename: str = None) -> Dict:
        """
        Read cloud builder meta data file for the given package

        :param str package_path: path to package sources
        :param str filename:
            alternative meta data file name, default is cloud_builder.yml

        :return: yaml dictionary data

        :rtype: Dict
        """
        config_file = filename or os.path.join(
            package_path, 'cloud_builder.yml'
        )
        with open(config_file, 'r') as config:
            return yaml.safe_load(config) or {}

    @staticmethod
    def get_kafka_config() -> str:
        """
        Location of kafka access credentials

        :return: A file path

        :rtype: str
        """
        return os.path.join(Defaults.__conf_path(), 'kafka.yml')

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
