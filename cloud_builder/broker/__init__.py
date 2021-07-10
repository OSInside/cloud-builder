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
import importlib
from abc import (
    ABCMeta,
    abstractmethod
)

# project
from cloud_builder.exceptions import CBMessageBrokerSetupError


class CBMessageBroker(metaclass=ABCMeta):
    """
    **CBMessageBroker factory**
    """
    @abstractmethod
    def __init__(self) -> None:
        return None  # pragma: no cover

    @staticmethod
    @abstractmethod
    def new(broker_name: str, config_file: str):
        """
        Create new instance of given message broker

        :param str broker_name: broker name
        :param str config_file: a yaml config file
        """
        name_map = {
            'kafka': 'CBMessageBrokerKafka'
        }
        try:
            broker = importlib.import_module(
                f'cloud_builder.broker.{broker_name}'
            )
            module_name = name_map[broker_name]
            return broker.__dict__[module_name](
                config_file
            )
        except Exception as issue:
            raise CBMessageBrokerSetupError(
                f'No support for {broker_name} message broker: {issue}'
            )
