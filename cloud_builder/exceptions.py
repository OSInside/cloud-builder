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
import sys
from functools import wraps
from typing import Callable
from cloud_builder.logger import CBLogger
from kiwi.exceptions import KiwiError


def exception_handler(func: Callable) -> Callable:
    """
    Decorator method to add exception handling
    Methods marked with this decorator are called under
    control of the cloud builder exceptions

    :param Callable func: Function pointer

    :return: func, wrapped with exception handling

    :rtype: Callable
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        log = CBLogger.get_logger()
        try:
            return func(*args, **kwargs)
        except CBError as issue:
            # known exception, log information and exit
            log.error(f'{type(issue).__name__}: {issue}')
            sys.exit(1)
        except KiwiError as issue:
            # known exception, log information and exit
            log.error(f'{type(issue).__name__}: {issue}')
            sys.exit(1)
        except KeyboardInterrupt:
            log.error('Exit on keyboard interrupt')
            sys.exit(1)
        except SystemExit as issue:
            # user exception, program aborted by user
            sys.exit(issue)
        except Exception:
            # exception we did no expect, show python backtrace
            log.error('Unexpected error:')
            raise
    return wrapper


class CBError(Exception):
    """
    Base class to handle all known exceptions

    Specific exceptions are implemented as sub classes of CBError
    """
    def __init__(self, message) -> None:
        """
        Store exception message

        :param str message: Exception message text
        """
        self.message = message

    def __str__(self) -> str:
        """
        Return representation of exception message

        :return: A message

        :rtype: str
        """
        return format(self.message)


class CBConfigFileValidationError(CBError):
    """
    Exception raised if the config file is invalid against its schema
    """


class CBConfigFileNotFoundError(CBError):
    """
    Exception raised if a config file could not be found
    """


class CBKafkaProducerException(CBError):
    """
    Exception raised if an instance of KafkaProducer
    returned an error
    """


class CBKafkaConsumerException(CBError):
    """
    Exception raised if an instance of KafkaConsumer
    returned an error
    """


class CBMessageBrokerSetupError(CBError):
    """
    Exception raised if there is no implementation for the
    selected message broker
    """


class CBSchedulerIntervalError(CBError):
    """
    Exception raised if the update interval for the BlockingScheduler
    is smaller than the poll timeout of the message broker
    """
