from mock import (
    Mock, patch
)
from pytest import raises

from cloud_builder.exceptions import exception_handler
from kiwi.exceptions import KiwiError


class TestExceptions:
    @patch('cloud_builder.exceptions.CBLogger.get_logger')
    @patch('sys.exit')
    def test_exception_handler_keyboard_interrupt(
        self, mock_sys_exit, mock_get_logger
    ):
        log = mock_get_logger.return_value
        func = Mock()

        func.side_effect = KeyboardInterrupt
        wrapper = exception_handler(func)
        wrapper()
        log.error.assert_called_once_with('Exit on keyboard interrupt')
        mock_sys_exit.assert_called_once_with(1)

    @patch('cloud_builder.exceptions.CBLogger.get_logger')
    @patch('sys.exit')
    def test_exception_handler_system_exit(
        self, mock_sys_exit, mock_get_logger
    ):
        func = Mock()

        func.side_effect = SystemExit
        wrapper = exception_handler(func)
        wrapper()
        assert mock_sys_exit.called

    @patch('cloud_builder.exceptions.CBLogger.get_logger')
    @patch('sys.exit')
    def test_exception_handler_kiwi_error(
        self, mock_sys_exit, mock_get_logger
    ):
        log = mock_get_logger.return_value
        func = Mock()

        func.side_effect = KiwiError('kiwi_issue')
        wrapper = exception_handler(func)
        wrapper()
        log.error.assert_called_once_with('KiwiError: kiwi_issue')
        mock_sys_exit.assert_called_once_with(1)

    @patch('cloud_builder.exceptions.CBLogger.get_logger')
    def test_exception_handler_unexpected_error(
        self, mock_get_logger
    ):
        log = mock_get_logger.return_value
        func = Mock()

        func.side_effect = Exception
        wrapper = exception_handler(func)
        with raises(Exception):
            wrapper()
        log.error.assert_called_once_with('Unexpected error:')
