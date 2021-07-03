import yaml
from mock import patch

from cloud_builder.cloud_logger import CBCloudLogger


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

    def test_response(self):
        message_dict = {
            'message': 'message'
        }
        self.cloud_logger.response(message_dict)
        self.cloud_logger.log.info.assert_called_once_with(
            '{0}: {1}'.format(
                self.cloud_logger.id, yaml.dump(message_dict).encode()
            )
        )
