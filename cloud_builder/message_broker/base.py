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
import yaml
from abc import ABCMeta, abstractmethod
from cerberus import Validator
from typing import (
    Dict, List
)
from cloud_builder.package_request import CBPackageRequest
from cloud_builder.package_request_schema import package_request_schema
from cloud_builder.cloud_logger import CBCloudLogger

from cloud_builder.exceptions import CBConfigFileNotFoundError


class CBMessageBrokerBase(metaclass=ABCMeta):
    """
    Interface for message handling in the context of Cloud Builder
    """
    def __init__(self, config_file: str) -> None:
        """
        Create a new instance of CBMessageBrokerBase

        :param str config_file: a yaml config file
        """
        try:
            with open(config_file, 'r') as config:
                self.config = yaml.safe_load(config)
        except Exception as issue:
            raise CBConfigFileNotFoundError(issue)

        self.log = CBCloudLogger(
            'CBMessageBrokerBase', '(system)'
        )
        self.post_init()

    @abstractmethod
    def post_init(self):
        pass

    def validate_package_request(self, message: str) -> Dict:
        """
        Validate a package build request

        Invalid messages will be auto committed such that they
        don't appear again

        :param str message: raw message

        :return: yaml formatted dict

        :rtype: str
        """
        message_as_yaml = {}
        try:
            message_as_yaml = yaml.safe_load(message)
            validator = Validator(package_request_schema)
            validator.validate(
                message_as_yaml, package_request_schema
            )
            if validator.errors:
                self.log.error(
                    'Validation for "{0}" failed with: {1}'.format(
                        message_as_yaml, validator.errors
                    )
                )
                self.acknowledge()
        except yaml.YAMLError as issue:
            self.log.error(
                'YAML load for "{0}" failed with: "{1}"'.format(
                    message, issue
                )
            )
            self.acknowledge()
        return message_as_yaml

    @abstractmethod
    def send_package_request(self, request: CBPackageRequest) -> None:
        """
        Send a package build request

        Implementation in specialized broker class

        :param CBPackageRequest request: unused
        """
        raise NotImplementedError

    @abstractmethod
    def acknowledge(self) -> None:
        """
        Acknowledge message so we don't get it again

        Implementation in specialized broker class
        """
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """
        Close connection to message system

        Implementation in specialized broker class
        """
        raise NotImplementedError

    @abstractmethod
    def read(
        self, topic: str, client: str = 'cb-client',
        group: str = 'cb-group', timeout_ms: int = 1000
    ) -> List:
        """
        Read messages from message system.

        Implementation in specialized broker class

        :param str topic: unused
        :param str client: unused
        :param str group: unused
        :param int timeout_ms: unused

        :return: list of raw results

        :rtype: List
        """
        raise NotImplementedError
