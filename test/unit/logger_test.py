import sys
from tempfile import NamedTemporaryFile
import logging
from mock import (
    patch, Mock
)

from cloud_builder.logger import CBLogger


class TestCBLogger:
    @patch('cloud_builder.logger.CBLogger.hasFileHandler')
    @patch('logging.getLogger')
    @patch('logging.StreamHandler')
    @patch('logging.FileHandler')
    def test_get_logger(
        self, mock_logging_FileHandler, mock_logging_StreamHandler,
        mock_logging_getLogger, mock_CBLogger_hasFileHandler
    ):
        log = Mock()
        log.hasHandlers.return_value = False
        mock_logging_getLogger.return_value = log
        mock_CBLogger_hasFileHandler.return_value = False
        assert CBLogger.get_logger('logfile') == log
        log.setLevel.assert_called_once_with(logging.INFO)
        mock_logging_getLogger.assert_called_once_with('CB')
        mock_logging_StreamHandler.assert_called_once_with(sys.stdout)
        mock_logging_FileHandler.assert_called_once_with(
            filename='logfile', encoding='utf-8'
        )

    @patch('logging.getLogger')
    def test_hasFileHandler(self, mock_logging_getLogger):
        logfile = NamedTemporaryFile()
        log = Mock()
        log.handlers = [logging.FileHandler(logfile.name)]
        mock_logging_getLogger.return_value = log
        assert CBLogger.hasFileHandler() is True
        log.handlers = []
        assert CBLogger.hasFileHandler() is False
