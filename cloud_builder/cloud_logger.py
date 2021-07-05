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
from cloud_builder.logger import CBLogger
from cloud_builder.defaults import Defaults
from cloud_builder.identity import CBIdentity
from typing import Dict


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
        Local log for info message

        :param str message: message
        """
        self.log.info(f'{self.id}: {message}')

    def warning(self, message: str) -> None:
        """
        Local log for warning message

        :param str message: message
        """
        self.log.warning(f'{self.id}: {message}')

    def error(self, message: str) -> None:
        """
        Local log for error message

        :param str message: message
        """
        self.log.error(f'{self.id}: {message}')

    def response(self, message: Dict) -> None:
        """
        Message broker plus local info log for
        response message

        :param dict message: yaml dict message
        """
        self.log.info(
            '{0}: {1}'.format(self.id, yaml.dump(message).encode())
        )
        # TODO: send this information to Defaults.get_response_queue_name()
