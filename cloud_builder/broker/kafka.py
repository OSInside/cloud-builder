# Copyright (c) 2021 Marcus Schaefer.  All rights reserved.
#
# This file is part of Cloud Builder.
#
# Cloud Builder is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Cloud Builder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Cloud Builder.  If not, see <http://www.gnu.org/licenses/>
#
import yaml
import logging
from typing import List
from kafka import KafkaConsumer
from kafka import KafkaProducer
from cerberus import Validator

from cloud_builder.defaults import Defaults
from cloud_builder.build_request.build_request import CBBuildRequest
from cloud_builder.info_request.info_request import CBInfoRequest
from cloud_builder.response.response import CBResponse
from cloud_builder.info_response.info_response import CBInfoResponse
from cloud_builder.broker.base import CBMessageBrokerBase
from cloud_builder.config.cloud_builder_broker_schema import (
    cloud_builder_broker_schema
)

from cloud_builder.exceptions import (
    CBKafkaProducerException,
    CBKafkaConsumerException,
    CBConfigFileValidationError
)

log = logging.getLogger('cloud_builder')


class CBMessageBrokerKafka(CBMessageBrokerBase):
    """
    Interface for kafka message handling in the context of Cloud Builder
    """
    def post_init(self) -> None:
        """
        Create a new instance of CBMessageBrokerKafka

        :param str config_file: Kafka credentials file

        .. code:: yaml
            host: kafka-example.com:12345
        """
        validator = Validator(cloud_builder_broker_schema)
        validator.validate(self.config, cloud_builder_broker_schema)
        if validator.errors:
            raise CBConfigFileValidationError(
                'ValidationError for {0!r}: {1!r}'.format(
                    self.config, validator.errors
                )
            )
        self.kafka_host = self.config['broker']['host']
        self.tls = self.config['broker'].get('tls')
        if self.tls:
            self.kafka_ca = self.tls['ssl_cafile']
            self.kafka_cert = self.tls['ssl_certfile']
            self.kafka_key = self.tls['ssl_keyfile']
        self.consumer: KafkaConsumer = None
        self.producer: KafkaProducer = None

    def send_build_request(self, request: CBBuildRequest) -> None:
        """
        Send a package/image build request

        Send a message conforming to the build_request_schema
        to kafka. The information for the message is taken from
        an instance of CBBuildRequest

        :param CBBuildRequest request: Instance of CBBuildRequest
        """
        self._create_producer()
        message = yaml.dump(request.get_data()).encode()
        self.producer.send(
            request.get_data()['runner_group'], message
        ).add_callback(self._on_send_success).add_errback(self._on_send_error)
        self.producer.flush()

    def send_info_request(self, request: CBInfoRequest) -> None:
        """
        Send a info request

        Send a message conforming to the info_request_schema
        to kafka. The information for the message is taken from
        an instance of CBInfoRequest

        :param CBInfoRequest request: Instance of CBInfoRequest
        """
        self._create_producer()
        message = yaml.dump(request.get_data()).encode()
        self.producer.send(
            Defaults.get_info_request_queue_name(), message
        ).add_callback(self._on_send_success).add_errback(self._on_send_error)
        self.producer.flush()

    def send_response(self, response: CBResponse) -> None:
        """
        Send a response

        Send a message conforming to the response_schema
        to kafka. The information for the message is taken from
        an instance of CBResponse

        :param CBResponse response: Instance of CBResponse
        """
        self._create_producer()
        message = yaml.dump(response.get_data()).encode()
        self.producer.send(
            Defaults.get_response_queue_name(), message
        ).add_callback(self._on_send_success).add_errback(self._on_send_error)
        self.producer.flush()

    def send_info_response(self, response: CBInfoResponse) -> None:
        """
        Send a info response

        Send a message conforming to the info_response_schema
        to kafka. The information for the message is taken from
        an instance of CBInfoResponse

        :param CBInfoResponse response: Instance of CBInfoResponse
        """
        self._create_producer()
        message = yaml.dump(response.get_data()).encode()
        self.producer.send(
            Defaults.get_info_response_queue_name(), message
        ).add_callback(self._on_send_success).add_errback(self._on_send_error)
        self.producer.flush()

    def acknowledge(self) -> None:
        """
        Acknowledge message so we don't get it again
        """
        if self.consumer:
            self.consumer.commit()

    def get_runner_group(self) -> str:
        """
        Return runner identification for package build requests.
        In kafka this is the topic name of the request queue

        :return: kafka topic name

        :rtype: str
        """
        if self.config.get('runner'):
            return self.config['runner']['group']
        return Defaults.get_build_request_queue_name()

    def close(self) -> None:
        """
        Close connection to message system
        """
        if self.consumer:
            self.consumer.close()

    def read(
        self, topic: str, client: str = 'cb-client',
        group: str = 'cb-group', timeout_ms: int = 1000
    ) -> List:
        """
        Read messages from message system.

        :param str topic: kafka topic
        :param str client: kafka consumer client name
        :param str group: kafka consumer group name
        :param int timeout_ms: read timeout in ms

        :return: list of Kafka poll results

        :rtype: List
        """
        message_data = []
        self._create_consumer(topic, client, group)
        raw_messages = self.consumer.poll(timeout_ms=timeout_ms)
        for topic_partition, message_list in raw_messages.items():
            for message in message_list:
                message_data.append(message)
        return message_data

    def _on_send_success(self, record_metadata):
        """
        Callback for successful sending of a message
        """
        log.debug(
            f'Message successfully sent to: {record_metadata.topic}'
        )

    def _on_send_error(self, exception):
        """
        Callback for error sending of a message
        """
        log.debug(
            f'Message failed with: {exception}'
        )

    def _create_producer(self) -> None:
        """
        Create a KafkaProducer
        """
        if not self.producer:
            try:
                producer_setup = {
                    'bootstrap_servers': self.kafka_host
                }
                if self.tls:
                    producer_setup['security_protocol'] = 'SSL'
                    producer_setup['ssl_cafile'] = self.kafka_ca
                    producer_setup['ssl_certfile'] = self.kafka_cert
                    producer_setup['ssl_keyfile'] = self.kafka_key
                self.producer = KafkaProducer(**producer_setup)
            except Exception as issue:
                raise CBKafkaProducerException(
                    f'Creating kafka producer failed with: {issue!r}'
                )

    def _create_consumer(
        self, topic: str, client: str, group: str
    ) -> None:
        """
        Create a KafkaConsumer

        :param str topic: kafka topic
        :param str client: kafka consumer client name
        :param str group: kafka consumer group name
        """
        if not self.consumer:
            try:
                consumer_setup = {
                    'enable_auto_commit': False,
                    'bootstrap_servers': self.kafka_host,
                    'client_id': client,
                    'group_id': group
                }
                if self.tls:
                    consumer_setup['security_protocol'] = 'SSL'
                    consumer_setup['ssl_cafile'] = self.kafka_ca
                    consumer_setup['ssl_certfile'] = self.kafka_cert
                    consumer_setup['ssl_keyfile'] = self.kafka_key
                self.consumer = KafkaConsumer(topic, **consumer_setup)
            except Exception as issue:
                raise CBKafkaConsumerException(
                    f'Creating kafka consumer failed with: {issue!r}'
                )
