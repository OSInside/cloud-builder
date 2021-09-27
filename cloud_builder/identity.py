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
import uuid
import yaml
from cloud_builder.defaults import Defaults


class CBIdentity:
    """
    Implements ID schema
    """
    @staticmethod
    def get_id(service: str, name: str) -> str:
        """
        Create identity string.

        The information consists out of the service name,
        the external host IP if obtainable, the PID of the caller
        process and some custom name which is usually a package or
        task name

        :param str service: service name
        :param str name: custom name

        :return: id string of the format: service:ip:pid:name

        :rtype: str
        """
        return f'{service}:{CBIdentity.get_external_ip()}:{os.getpid()}:{name}'

    @staticmethod
    def get_request_id() -> str:
        """
        Create a unique UUID, typically for a request to the system

        :return: UUID

        :rtype: str
        """
        return format(uuid.uuid1())

    @staticmethod
    def get_external_ip() -> str:
        """
        Read host IP/name from the broker configuration

        :return: host IP/location or 'unknown'

        :rtype: str
        """
        try:
            with open(Defaults.get_broker_config()) as config:
                return yaml.safe_load(config)['this_host']
        except Exception:
            return 'unknown'
