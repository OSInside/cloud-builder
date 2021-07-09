import yaml
import io
from mock import (
    patch, Mock, MagicMock, call
)

from cloud_builder.cloud_logger import CBCloudLogger
from cloud_builder.response import CBResponse
from cloud_builder.info_response import CBInfoResponse


class TestCBCloudLogger:
    @patch('cloud_builder.cloud_logger.CBLogger')
    @patch('cloud_builder.cloud_logger.CBIdentity')
    def setup(self, mock_CBIdentity, mock_CBLogger):
        self.cloud_logger = CBCloudLogger('service', 'name')

    def test_get_id(self):
        assert self.cloud_logger.get_id() == self.cloud_logger.id

    def test_info(self):
        self.cloud_logger.info('message')
        self.cloud_logger.log.info.assert_called_once_with(
            '{0}: {1}'.format(self.cloud_logger.id, 'message')
        )

    def test_warning(self):
        self.cloud_logger.warning('message')
        self.cloud_logger.log.warning.assert_called_once_with(
            '{0}: {1}'.format(self.cloud_logger.id, 'message')
        )

    def test_error(self):
        self.cloud_logger.error('message')
        self.cloud_logger.log.error.assert_called_once_with(
            '{0}: {1}'.format(self.cloud_logger.id, 'message')
        )

    def test_info_response(self):
        response = CBInfoResponse('UUID', 'response_identity')
        broker = Mock()
        self.cloud_logger.info_response(response, broker)
        self.cloud_logger.log.info.assert_called_once_with(
            '{0}: {1}'.format(
                self.cloud_logger.id, yaml.dump(response.get_data()).encode()
            )
        )
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
                call('0.1'),
                call('\n')
            ]
        self.cloud_logger.log.info.assert_called_once_with(
            '{0}: {1}'.format(
                self.cloud_logger.id, yaml.dump(response.get_data()).encode()
            )
        )
        broker.send_response.assert_called_once_with(response)
