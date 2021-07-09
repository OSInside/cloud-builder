from mock import (
    patch, Mock
)
from pytest import raises

from cloud_builder.message_broker.base import CBMessageBrokerBase
from cloud_builder.exceptions import CBConfigFileNotFoundError
from cloud_builder.schemas.package_request_schema import package_request_schema
from cloud_builder.schemas.response_schema import response_schema
from cloud_builder.schemas.info_request_schema import info_request_schema
from cloud_builder.schemas.info_response_schema import info_response_schema


class TestCBMessageBrokerBase:
    @patch.multiple(CBMessageBrokerBase, __abstractmethods__=set())
    @patch('cloud_builder.message_broker.base.CBCloudLogger')
    def setup(self, mock_CBCloudLogger):
        self.log = mock_CBCloudLogger.return_value
        self.broker = CBMessageBrokerBase(config_file='../data/cb/kafka.yml')

    @patch.multiple(CBMessageBrokerBase, __abstractmethods__=set())
    def test_setup_raises_no_broker_config(self):
        with raises(CBConfigFileNotFoundError):
            CBMessageBrokerBase(config_file='artificial')

    def test_post_init(self):
        assert self.broker.post_init() is None

    @patch.object(CBMessageBrokerBase, 'validate_message_with_schema')
    def test_validate_package_request(self, mock_validate_message_with_schema):
        self.broker.validate_package_request('message')
        mock_validate_message_with_schema.assert_called_once_with(
            'message', package_request_schema
        )

    @patch.object(CBMessageBrokerBase, 'validate_message_with_schema')
    def test_validate_package_response(self, mock_validate_message_with_schema):
        self.broker.validate_package_response('message')
        mock_validate_message_with_schema.assert_called_once_with(
            'message', response_schema
        )

    @patch.object(CBMessageBrokerBase, 'validate_message_with_schema')
    def test_validate_info_request(self, mock_validate_message_with_schema):
        self.broker.validate_info_request('message')
        mock_validate_message_with_schema.assert_called_once_with(
            'message', info_request_schema
        )

    @patch.object(CBMessageBrokerBase, 'validate_message_with_schema')
    def test_validate_info_response(self, mock_validate_message_with_schema):
        self.broker.validate_info_response('message')
        mock_validate_message_with_schema.assert_called_once_with(
            'message', info_response_schema
        )

    @patch.object(CBMessageBrokerBase, 'acknowledge')
    def test_validate_message_with_schema_broken_yaml(self, mock_acknowledge):
        assert self.broker.validate_message_with_schema(
            'invalid_yaml', package_request_schema
        ) == {}
        for log_message in self.log.error.call_args_list[0][0]:
            assert 'DocumentError' in log_message
        mock_acknowledge.assert_called_once_with()

    @patch.object(CBMessageBrokerBase, 'acknowledge')
    def test_validate_message_with_schema_invalid_yaml(self, mock_acknowledge):
        assert self.broker.validate_message_with_schema(
            "{'foo': 'bar'}", package_request_schema
        ) == {}
        for log_message in self.log.error.call_args_list[0][0]:
            assert 'ValidationError' in log_message
        mock_acknowledge.assert_called_once_with()

    @patch.object(CBMessageBrokerBase, 'acknowledge')
    def test_validate_message_with_schema_ok(self, mock_acknowledge):
        assert self.broker.validate_message_with_schema(
            "{'schema_version': 0.1, 'request_id': 'uuid', "
            "'package': 'vim', 'arch': 'x86_64', 'action': 'action'}",
            package_request_schema
        ) == {
            'action': 'action',
            'arch': 'x86_64',
            'package': 'vim',
            'request_id': 'uuid',
            'schema_version': 0.1
        }
        assert not mock_acknowledge.called

    def test_send_package_request(self):
        with raises(NotImplementedError):
            self.broker.send_package_request(Mock())

    def test_send_response(self):
        with raises(NotImplementedError):
            self.broker.send_response(Mock())

    def test_send_info_response(self):
        with raises(NotImplementedError):
            self.broker.send_info_response(Mock())

    def test_acknowledge(self):
        with raises(NotImplementedError):
            self.broker.acknowledge()

    def test_close(self):
        with raises(NotImplementedError):
            self.broker.close()

    def test_read(self):
        with raises(NotImplementedError):
            self.broker.read('queue')
