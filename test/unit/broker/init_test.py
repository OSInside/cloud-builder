from pytest import raises
from mock import patch

from cloud_builder.exceptions import CBMessageBrokerSetupError
from cloud_builder.broker import CBMessageBroker


class TestCBMessageBroker:
    def test_broker_not_implemented(self):
        with raises(CBMessageBrokerSetupError):
            CBMessageBroker.new('artificial', 'broker_config_file')

    @patch('cloud_builder.broker.kafka.CBMessageBrokerKafka')
    def test_broker_kafka(self, mock_CBMessageBrokerKafka):
        CBMessageBroker.new('kafka', 'kafka_config_file')
        mock_CBMessageBrokerKafka.assert_called_once_with(
            'kafka_config_file'
        )
