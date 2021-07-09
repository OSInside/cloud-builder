from pytest import raises
from mock import (
    patch, Mock
)
import yaml
from cloud_builder.package_request import CBPackageRequest
from cloud_builder.response import CBResponse
from cloud_builder.info_response import CBInfoResponse
from cloud_builder.message_broker.kafka import CBMessageBrokerKafka
from cloud_builder.exceptions import (
    CBKafkaProducerException,
    CBKafkaConsumerException
)


class TestCBMessageBrokerKafka:
    @patch('cloud_builder.message_broker.kafka.CBCloudLogger')
    def setup(self, mock_CBCloudLogger):
        config_file = '../data/cb/kafka.yml'
        with open(config_file) as config:
            CBMessageBrokerKafka.__bases__ = (Mock,)
            self.log = mock_CBCloudLogger.return_value
            self.kafka = CBMessageBrokerKafka(config_file)
            self.kafka.config = yaml.safe_load(config)
            self.kafka.post_init()
        assert self.kafka.kafka_host == 'URI:9092'

    @patch('cloud_builder.message_broker.kafka.KafkaProducer')
    def test_create_producer_raises(self, mock_KafkaProducer):
        mock_KafkaProducer.side_effect = Exception
        with raises(CBKafkaProducerException):
            self.kafka._create_producer()

    @patch('cloud_builder.message_broker.kafka.KafkaConsumer')
    def test_create_consumer_raises(self, mock_KafkaConsumer):
        mock_KafkaConsumer.side_effect = Exception
        with raises(CBKafkaConsumerException):
            self.kafka._create_consumer('topic', 'client', 'group')

    @patch('cloud_builder.message_broker.kafka.KafkaProducer')
    def test_send_package_request(self, mock_KafkaProducer):
        producer = mock_KafkaProducer.return_value
        request = CBPackageRequest()
        self.kafka.send_package_request(request)
        producer.send.assert_called_once_with(
            'cb-package-request', yaml.dump(request.get_data()).encode()
        )
        producer.flush.assert_called_once_with()

    @patch('cloud_builder.message_broker.kafka.KafkaProducer')
    def test_send_response(self, mock_KafkaProducer):
        producer = mock_KafkaProducer.return_value
        response = CBResponse('request_id', 'identity')
        self.kafka.send_response(response)
        producer.send.assert_called_once_with(
            'cb-response', yaml.dump(response.get_data()).encode()
        )
        producer.flush.assert_called_once_with()

    @patch('cloud_builder.message_broker.kafka.KafkaProducer')
    def test_send_info_response(self, mock_KafkaProducer):
        producer = mock_KafkaProducer.return_value
        response = CBInfoResponse('request_id', 'identity')
        self.kafka.send_info_response(response)
        producer.send.assert_called_once_with(
            'cb-info-response', yaml.dump(response.get_data()).encode()
        )
        producer.flush.assert_called_once_with()

    def test_acknowledge(self):
        self.kafka.consumer = Mock()
        self.kafka.acknowledge()
        self.kafka.consumer.commit.assert_called_once_with()

    def test_close(self):
        self.kafka.consumer = Mock()
        self.kafka.close()
        self.kafka.consumer.close.assert_called_once_with()

    @patch('cloud_builder.message_broker.kafka.KafkaConsumer')
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

    def test_on_send_success(self):
        record_metadata = Mock()
        record_metadata.topic = 'topic'
        self.kafka._on_send_success(record_metadata)
        self.log.info.assert_called_once_with(
            'Message successfully sent to: topic'
        )

    def test_on_send_error(self):
        self.kafka._on_send_error('exception')
        self.log.error.assert_called_once_with(
            'Message failed with: exception'
        )
