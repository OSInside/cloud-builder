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
from typing import (
    Any, Dict
)
from cloud_builder.logger import CBLogger
from cloud_builder.defaults import Defaults
from cloud_builder.identity import CBIdentity
from cloud_builder.response.response import CBResponse
from cloud_builder.info_response.info_response import CBInfoResponse


class CBCloudLogger:
    def __init__(self, service: str, name: str) -> None:
        """
        Create a logger object for local logging and
        logging of response messages to the message broker
        response queue

        :param str service: service name
        :param str name: custom name
        """
        self.log = CBLogger.get_logger(
            logfile=Defaults.get_cb_logfile()
        )
        self.id = CBIdentity.get_id(service, name)

    def get_id(self) -> str:
        """
        Return log prefix ID

        :return: ID string from CBIdentity.get_id

        :rtype: str
        """
        return self.id

    def info(self, message: str) -> None:
        """
        Local log an info message

        :param str message: message
        """
        self.log.info(f'{self.id}: {message}')

    def warning(self, message: str) -> None:
        """
        Local log a warning message

        :param str message: message
        """
        self.log.warning(f'{self.id}: {message}')

    def error(self, message: str) -> None:
        """
        Local log an error message

        :param str message: message
        """
        self.log.error(f'{self.id}: {message}')

    def info_response(
        self, response: CBInfoResponse, broker: Any, filename: str = None
    ) -> None:
        """
        Local and message broker log a CBInfoResponse message

        :param CBInfoResponse response: instance of CBInfoResponse
        :param CBMessageBroker broker: instance of CBMessageBroker
        :param str filename: store to filename in yaml format
        """
        self._process_response(response.get_data(), filename)
        broker.send_info_response(response)

    def response(
        self, response: CBResponse, broker: Any, filename: str = None
    ) -> None:
        """
        Local and message broker log a CBResponse message

        :param CBResponse response: instance of CBResponse
        :param CBMessageBroker broker: instance of CBMessageBroker
        :param str filename: store to filename in yaml format
        """
        self._process_response(response.get_data(), filename)
        broker.send_response(response)

    def _process_response(
        self, response_dict: Dict, filename: str = None
    ) -> None:
        """
        Local log a response_dict

        :param Dict response_dict: message dict
        :param str filename: store to filename in yaml format
        """
        self.log.info(
            '{0}: {1}'.format(
                self.id, yaml.dump(response_dict).encode()
            )
        )
        if filename:
            with open(filename, 'w') as out:
                yaml.dump(
                    response_dict, out, default_flow_style=False
                )
