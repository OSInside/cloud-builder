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
from cerberus import Validator
from cloud_builder.package_metadata.package_metadata_schema import (
    package_metadata_schema
)
from cloud_builder.cloud_logger import CBCloudLogger
from cloud_builder.broker import CBMessageBroker
from cloud_builder.response.response import CBResponse
from cloud_builder.defaults import Defaults
from typing import Dict


class CBPackageMetaData:
    """
    Implements Cloud Builder metadata handling
    """
    @staticmethod
    def get_package_config(
        package_path: str, log: CBCloudLogger, request_id: str,
        filename: str = None
    ) -> Dict:
        """
        Read cloud builder meta data file for the given package

        :param str package_path: path to package sources
        :param CBCloudLogger log: CBCloudLogger object instance
        :param str request_id: UUID
        :param str filename:
            alternative meta data file name, default is
            Defaults.get_cloud_builder_metadata_file_name()

        :return: yaml dictionary data or empty dict

        :rtype: Dict
        """
        config_data: Dict[str, str] = {}
        config_file = filename or os.path.join(
            package_path, Defaults.get_cloud_builder_metadata_file_name()
        )
        if os.path.isfile(config_file):
            with open(config_file, 'r') as config:
                try:
                    config_data = yaml.safe_load(config) or {}
                    validator = Validator(package_metadata_schema)
                    validator.validate(
                        config_data, package_metadata_schema
                    )
                    if validator.errors:
                        broker = CBMessageBroker.new(
                            'kafka', config_file=Defaults.get_broker_config()
                        )
                        status_flags = Defaults.get_status_flags()
                        response = CBResponse(request_id, log.get_id())
                        response.set_package_invalid_metadata_response(
                            message='ValidationError in {0!r}: {1!r}'.format(
                                config_file, validator.errors
                            ),
                            response_code=status_flags.invalid_metadata,
                            package=package_path
                        )
                        log.response(response, broker)
                        config_data = {}
                except Exception as issue:
                    broker = CBMessageBroker.new(
                        'kafka', config_file=Defaults.get_broker_config()
                    )
                    status_flags = Defaults.get_status_flags()
                    response = CBResponse(request_id, log.get_id())
                    response.set_package_invalid_metadata_response(
                        message='YAMLError in {0!r}: {1!r}'.format(
                            config_file, issue
                        ),
                        response_code=status_flags.invalid_metadata,
                        package=package_path
                    )
                    log.response(response, broker)
                    config_data = {}
        return config_data
