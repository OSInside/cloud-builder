import logging
from mock import (
    patch, Mock
)
from pytest import (
    raises, fixture
)

from cloud_builder.broker.base import CBMessageBrokerBase
from cloud_builder.exceptions import CBConfigFileNotFoundError
from cloud_builder.build_request.build_request_schema import (
    build_request_schema
)
from cloud_builder.response.response_schema import response_schema
from cloud_builder.info_request.info_request_schema import info_request_schema
from cloud_builder.info_response.info_response_schema import (
    info_response_schema
)


class TestCBMessageBrokerBase:
    @fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    @patch.multiple(CBMessageBrokerBase, __abstractmethods__=set())
    def setup(self):
        self.broker = CBMessageBrokerBase(
            config_file='../data/etc/cloud_builder_broker.yml',
            custom_args={}
        )

    @patch.multiple(CBMessageBrokerBase, __abstractmethods__=set())
    def setup_method(self, cls):
        self.setup()

    @patch.multiple(CBMessageBrokerBase, __abstractmethods__=set())
    def test_setup_raises_no_broker_config(self):
        with raises(CBConfigFileNotFoundError):
            CBMessageBrokerBase(config_file='artificial', custom_args={})

    def test_post_init(self):
        assert self.broker.post_init() is None

    @patch.object(CBMessageBrokerBase, 'validate_message_with_schema')
    def test_validate_package_request(self, mock_validate_message_with_schema):
        self.broker.validate_build_request('message')
        mock_validate_message_with_schema.assert_called_once_with(
            'message', build_request_schema
        )

    @patch.object(CBMessageBrokerBase, 'validate_message_with_schema')
    def test_validate_build_response(self, mock_validate_message_with_schema):
        self.broker.validate_build_response('message')
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
        with self._caplog.at_level(logging.DEBUG):
            assert self.broker.validate_message_with_schema(
                'invalid_yaml', build_request_schema
            ) == {}
            assert format('DocumentError') in self._caplog.text
            mock_acknowledge.assert_called_once_with()

    @patch.object(CBMessageBrokerBase, 'acknowledge')
    def test_validate_message_with_schema_invalid_yaml(self, mock_acknowledge):
        with self._caplog.at_level(logging.DEBUG):
            assert self.broker.validate_message_with_schema(
                "{'foo': 'bar'}", build_request_schema
            ) == {}
            assert format('ValidationError') in self._caplog.text
            mock_acknowledge.assert_called_once_with()

    @patch.object(CBMessageBrokerBase, 'acknowledge')
    def test_validate_message_with_schema_ok(self, mock_acknowledge):
        assert self.broker.validate_message_with_schema(
            "{'schema_version': 0.2, 'request_id': 'uuid', "
            "'project': 'vim', 'package': {'arch': 'x86_64', 'dist': 'TW'}, "
            "'runner_group': 'suse', 'action': 'action'}",
            build_request_schema
        ) == {
            'action': 'action',
            'package': {
                'arch': 'x86_64',
                'dist': 'TW'
            },
            'runner_group': 'suse',
            'project': 'vim',
            'request_id': 'uuid',
            'schema_version': 0.2
        }
        assert not mock_acknowledge.called

    def test_send_build_request(self):
        with raises(NotImplementedError):
            self.broker.send_build_request(Mock())

    def test_send_info_request(self):
        with raises(NotImplementedError):
            self.broker.send_info_request(Mock())

    def test_send_response(self):
        with raises(NotImplementedError):
            self.broker.send_response(Mock())

    def test_send_info_response(self):
        with raises(NotImplementedError):
            self.broker.send_info_response(Mock())

    def test_acknowledge(self):
        with raises(NotImplementedError):
            self.broker.acknowledge()

    def test_get_runner_group(self):
        with raises(NotImplementedError):
            self.broker.get_runner_group()

    def test_close(self):
        with raises(NotImplementedError):
            self.broker.close()

    def test_read(self):
        with raises(NotImplementedError):
            self.broker.read('queue')
