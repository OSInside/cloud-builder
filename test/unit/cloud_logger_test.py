import yaml
import io
from pytest import fixture
from mock import (
    patch, Mock, MagicMock, call
)
import logging
from cloud_builder.cloud_logger import CBCloudLogger
from cloud_builder.response.response import CBResponse
from cloud_builder.broker.base import CBMessageBrokerBase
from cloud_builder.info_response.info_response import CBInfoResponse


class TestCBCloudLogger:
    @fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    @patch.multiple(CBMessageBrokerBase, __abstractmethods__=set())
    @patch('cloud_builder.cloud_logger.CBIdentity')
    def setup(self, mock_CBIdentity, mock_abstracts):
        self.cloud_logger = CBCloudLogger('service', 'name')

    @patch('kiwi.logger.Logger.set_logfile')
    def test_set_logfile(self, mock_set_logfile):
        self.cloud_logger.set_logfile()
        mock_set_logfile.assert_called_once_with(
            '/var/log/cloud_builder.log'
        )

    @patch('kiwi.logger.Logger.setLevel')
    def test_set_loglevel(self, mock_setLevel):
        self.cloud_logger.set_loglevel(42)
        mock_setLevel.assert_called_once_with(42)

    def test_get_id(self):
        assert self.cloud_logger.get_id() == self.cloud_logger.id

    @patch('cloud_builder.cloud_logger.CBIdentity')
    def test_set_id(self, mock_CBIdentity):
        self.cloud_logger.set_id('new_name')
        assert self.cloud_logger.get_id() == self.cloud_logger.id

    def test_info(self):
        with self._caplog.at_level(logging.INFO):
            self.cloud_logger.info('message')
            assert '{0}: {1}'.format(
                self.cloud_logger.id, 'message'
            ) in self._caplog.text

    def test_warning(self):
        with self._caplog.at_level(logging.WARNING):
            self.cloud_logger.warning('message')
            assert '{0}: {1}'.format(
                self.cloud_logger.id, 'message'
            ) in self._caplog.text

    def test_error(self):
        with self._caplog.at_level(logging.ERROR):
            self.cloud_logger.error('message')
            assert '{0}: {1}'.format(
                self.cloud_logger.id, 'message'
            ) in self._caplog.text

    def test_info_response(self):
        response = CBInfoResponse('UUID', 'response_identity')
        broker = Mock()
        with self._caplog.at_level(logging.INFO):
            self.cloud_logger.info_response(response, broker)
            assert '{0}: {1}'.format(
                self.cloud_logger.id, yaml.dump(response.get_data()).encode()
            ) in self._caplog.text
            broker.send_info_response.assert_called_once_with(response)

    def test_response(self):
        response = CBResponse('UUID', 'response_identity')
        broker = Mock()
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            self.cloud_logger.response(response, broker, 'outfile.yml')
            assert file_handle.write.call_args_list == [
                call('identity'),
                call(':'),
                call(' '),
                call('response_identity'),
                call('\n'),
                call('request_id'),
                call(':'),
                call(' '),
                call('UUID'),
                call('\n'),
                call('schema_version'),
                call(':'),
                call(' '),
                call('0.2'),
                call('\n')
            ]
            assert '{0}: {1}'.format(
                self.cloud_logger.id, yaml.dump(response.get_data()).encode()
            ) in self._caplog.text
        broker.send_response.assert_called_once_with(response)
