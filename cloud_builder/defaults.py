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
        ('package_changed', str)
    ]
)


class Defaults:
    """
    Implements Cloud Builder project default values
    """
    @staticmethod
    def get_status_flags() -> status_flags:
        return status_flags(
            package_changed='package source changed'
        )

    @staticmethod
    def get_runner_project_dir() -> str:
        return f'{os.environ.get("HOME")}/cloud_builder_sources'

    @staticmethod
    def get_package_config(package_path: str, filename: str = None) -> Dict:
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
