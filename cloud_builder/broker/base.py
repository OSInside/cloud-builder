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
import logging
from abc import ABCMeta, abstractmethod
from cerberus import Validator
from typing import (
    Dict, List
)
from cloud_builder.build_request.build_request import CBBuildRequest
from cloud_builder.response.response import CBResponse
from cloud_builder.info_response.info_response import CBInfoResponse
from cloud_builder.info_request.info_request import CBInfoRequest
from cloud_builder.build_request.build_request_schema import (
    build_request_schema
)
from cloud_builder.response.response_schema import response_schema
from cloud_builder.info_request.info_request_schema import info_request_schema
from cloud_builder.info_response.info_response_schema import (
    info_response_schema
)
from cloud_builder.exceptions import CBConfigFileNotFoundError

log = logging.getLogger('cloud_builder')


class CBMessageBrokerBase(metaclass=ABCMeta):
    """
    Interface for message handling in the context of Cloud Builder
    """
    def __init__(self, config_file: str, custom_args: Dict) -> None:
        """
        Create a new instance of CBMessageBrokerBase

        :param str config_file: a yaml config file
        """
        self.config = {}
        if config_file:
            try:
                with open(config_file, 'r') as config:
                    self.config = yaml.safe_load(config)
            except Exception as issue:
                raise CBConfigFileNotFoundError(issue)
        self.custom_args = custom_args
        self.post_init()

    @abstractmethod
    def post_init(self) -> None:
        pass

    def validate_build_request(self, message: str) -> Dict:
        """
        Validate a build build request

        Invalid messages will be auto committed such that they
        don't appear again

        :param str message: raw message

        :return: yaml formatted dict

        :rtype: str
        """
        return self.validate_message_with_schema(
            message, build_request_schema
        )

    def validate_build_response(self, message: str) -> Dict:
        """
        Validate a build response

        Invalid messages will be auto committed such that they
        don't appear again

        :param str message: raw message

        :return: yaml formatted dict

        :rtype: str
        """
        return self.validate_message_with_schema(
            message, response_schema
        )

    def validate_info_request(self, message: str) -> Dict:
        """
        Validate a info request

        Invalid messages will be auto committed such that they
        don't appear again

        :param str message: raw message

        :return: yaml formatted dict

        :rtype: str
        """
        return self.validate_message_with_schema(
            message, info_request_schema
        )

    def validate_info_response(self, message: str) -> Dict:
        """
        Validate a info response

        Invalid messages will be auto committed such that they
        don't appear again

        :param str message: raw message

        :return: yaml formatted dict

        :rtype: str
        """
        return self.validate_message_with_schema(
            message, info_response_schema
        )

    def validate_message_with_schema(self, message: str, schema: Dict) -> Dict:
        """
        Validate a message against a given schema

        Invalid messages will be auto committed such that they
        don't appear again

        :param str message: raw message
        :param Dict schema: Cerberus schema dict

        :return: yaml formatted dict

        :rtype: str
        """
        message_as_yaml = {}
        try:
            message_as_yaml = yaml.safe_load(message)
            validator = Validator(schema)
            validator.validate(message_as_yaml, schema)
            if validator.errors:
                log.debug(
                    'ValidationError for {0!r}: {1!r}'.format(
                        message_as_yaml, validator.errors
                    )
                )
                message_as_yaml = {}
                self.acknowledge()
        except Exception as issue:
            log.debug(
                'YAMLError in {0!r}: {1!r}'.format(
                    message, issue
                )
            )
            message_as_yaml = {}
            self.acknowledge()
        return message_as_yaml

    @abstractmethod
    def send_build_request(self, request: CBBuildRequest) -> None:
        """
        Send a package/image build request

        Implementation in specialized broker class

        :param CBBuildRequest request: unused
        """
        raise NotImplementedError

    @abstractmethod
    def send_info_request(self, request: CBInfoRequest) -> None:
        """
        Send an info request

        Implementation in specialized broker class

        :param CBInfoRequest request: unused
        """
        raise NotImplementedError

    @abstractmethod
    def send_response(self, response: CBResponse) -> None:
        """
        Send a response

        Implementation in specialized broker class

        :param CBResponse response: unused
        """
        raise NotImplementedError

    @abstractmethod
    def send_info_response(self, response: CBInfoResponse) -> None:
        """
        Send a info response

        Implementation in specialized broker class

        :param CBInfoResponse response: unused
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
    def get_runner_group(self) -> str:
        """
        Return runner identification for package build requests

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
