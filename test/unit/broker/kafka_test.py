import logging
from pytest import (
    raises, fixture
)
from mock import (
    patch, Mock
)
import yaml
from cloud_builder.build_request.build_request import CBBuildRequest
from cloud_builder.info_request.info_request import CBInfoRequest
from cloud_builder.response.response import CBResponse
from cloud_builder.info_response.info_response import CBInfoResponse
from cloud_builder.broker.kafka import CBMessageBrokerKafka
from cloud_builder.exceptions import (
    CBKafkaProducerException,
    CBKafkaConsumerException,
    CBConfigFileValidationError
)


class TestCBMessageBrokerKafka:
    @fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    def setup(self):
        config_file = '../data/etc/cloud_builder_broker.yml'
        with open(config_file) as config:
            CBMessageBrokerKafka.__bases__ = (Mock,)
            self.kafka = CBMessageBrokerKafka(config_file)
            self.kafka.config = yaml.safe_load(config)
            self.kafka.post_init()
        assert self.kafka.kafka_host == 'URI:9092'

    def test_setup_raises_invalid_config(self):
        config_file = '../data/etc/cloud_builder_broker-invalid.yml'
        with open(config_file) as config:
            CBMessageBrokerKafka.__bases__ = (Mock,)
            self.kafka = CBMessageBrokerKafka(config_file)
            self.kafka.config = yaml.safe_load(config)
            with raises(CBConfigFileValidationError):
                self.kafka.post_init()

    @patch('cloud_builder.broker.kafka.KafkaProducer')
    def test_create_producer_raises(self, mock_KafkaProducer):
        mock_KafkaProducer.side_effect = Exception
        with raises(CBKafkaProducerException):
            self.kafka._create_producer()

    @patch('cloud_builder.broker.kafka.KafkaConsumer')
    def test_create_consumer_raises(self, mock_KafkaConsumer):
        mock_KafkaConsumer.side_effect = Exception
        with raises(CBKafkaConsumerException):
            self.kafka._create_consumer('topic', 'client', 'group')

    @patch('cloud_builder.broker.kafka.KafkaProducer')
    def test_send_build_request(self, mock_KafkaProducer):
        producer = mock_KafkaProducer.return_value
        request = CBBuildRequest()
        request.build_request_dict['runner_group'] = 'runner_group'
        self.kafka.send_build_request(request)
        producer.send.assert_called_once_with(
            request.get_data()['runner_group'],
            yaml.dump(request.get_data()).encode()
        )
        producer.flush.assert_called_once_with()

    @patch('cloud_builder.broker.kafka.KafkaProducer')
    def test_send_info_request(self, mock_KafkaProducer):
        producer = mock_KafkaProducer.return_value
        request = CBInfoRequest()
        self.kafka.send_info_request(request)
        producer.send.assert_called_once_with(
            'cb-info-request', yaml.dump(request.get_data()).encode()
        )
        producer.flush.assert_called_once_with()

    @patch('cloud_builder.broker.kafka.KafkaProducer')
    def test_send_response(self, mock_KafkaProducer):
        producer = mock_KafkaProducer.return_value
        response = CBResponse('request_id', 'identity')
        self.kafka.send_response(response)
        producer.send.assert_called_once_with(
            'cb-response', yaml.dump(response.get_data()).encode()
        )
        producer.flush.assert_called_once_with()

    @patch('cloud_builder.broker.kafka.KafkaProducer')
    def test_send_info_response(self, mock_KafkaProducer):
        producer = mock_KafkaProducer.return_value
        response = CBInfoResponse('request_id', 'identity')
        self.kafka.send_info_response(response)
        producer.send.assert_called_once_with(
            'cb-info-response', yaml.dump(response.get_data()).encode()
        )
        producer.flush.assert_called_once_with()
        mock_KafkaProducer.assert_called_once_with(
            bootstrap_servers='URI:9092',
            security_protocol='SSL',
            ssl_cafile='ca_file',
            ssl_certfile='cert_file',
            ssl_keyfile='key_file'
        )

    def test_acknowledge(self):
        self.kafka.consumer = Mock()
        self.kafka.acknowledge()
        self.kafka.consumer.commit.assert_called_once_with()

    def test_get_runner_group(self):
        assert self.kafka.get_runner_group() == 'fedora'
        self.kafka.config = {}
        assert self.kafka.get_runner_group() == 'cb-build-request'

    def test_close(self):
        self.kafka.consumer = Mock()
        self.kafka.close()
        self.kafka.consumer.close.assert_called_once_with()

    @patch('cloud_builder.broker.kafka.KafkaConsumer')
    def test_read(self, mock_KafkaConsumer):
        consumer = mock_KafkaConsumer.return_value
        TopicPartition = Mock()
        ConsumerRecord = Mock()
        mock_poll_result = {
            TopicPartition: [ConsumerRecord]
        }
        consumer.poll = Mock(
            return_value=mock_poll_result
        )
        assert self.kafka.read('topic') == [ConsumerRecord]
        mock_KafkaConsumer.assert_called_once_with(
            'topic',
            enable_auto_commit=False,
            bootstrap_servers='URI:9092',
            client_id='cb-client',
            group_id='cb-group',
            security_protocol='SSL',
            ssl_cafile='ca_file',
            ssl_certfile='cert_file',
            ssl_keyfile='key_file'
        )

    def test_on_send_success(self):
        record_metadata = Mock()
        record_metadata.topic = 'topic'
        with self._caplog.at_level(logging.DEBUG):
            self.kafka._on_send_success(record_metadata)
            assert format(
                'Message successfully sent to: topic'
            ) in self._caplog.text

    def test_on_send_error(self):
        with self._caplog.at_level(logging.DEBUG):
            self.kafka._on_send_error('exception')
            assert format(
                'Message failed with: exception'
            ) in self._caplog.text
