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
import logging
import sys
from logging import Logger


class CBLogger:
    """
    Implements the local CB logger
    """
    @staticmethod
    def get_logger(logfile: str = None, level: int = logging.INFO) -> Logger:
        """
        Configure CB logger

        Simple logger responding to logging.INFO level by default
        The logger is only created once, thus multiple get_logger()
        calls are allowed but the only the very first call will
        be effective on the level setting

        :param int level: log level

        :return: log handler

        :rtype: Logger
        """
        log = logging.getLogger('CB')
        log.setLevel(level)
        if not log.hasHandlers():
            channel = logging.StreamHandler(sys.stdout)
            channel.setLevel(level)
            log.addHandler(channel)

        if logfile and not CBLogger.hasFileHandler():
            logfile_handler = logging.FileHandler(
                filename=logfile, encoding='utf-8'
            )
            log.addHandler(logfile_handler)
        return log

    @staticmethod
    def hasFileHandler() -> bool:
        """
        Check if the logger has a file handler configured

        :return: True if logging.FileHandler handler exists else False

        :rtype: bool
        """
        log = logging.getLogger('CB')
        for handler in log.handlers:
            if isinstance(handler, logging.FileHandler):
                return True
        return False
