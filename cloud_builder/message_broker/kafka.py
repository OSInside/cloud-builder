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
from typing import List
from kafka import KafkaConsumer
from kafka import KafkaProducer

from cloud_builder.package_request import CBPackageRequest
from cloud_builder.cloud_logger import CBCloudLogger
from cloud_builder.message_broker.base import CBMessageBrokerBase

from cloud_builder.exceptions import (
    CBKafkaProducerException,
    CBKafkaConsumerException
)


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
        self.log = CBCloudLogger('CBMessageBrokerKafka', '(system)')
        self.kafka_host = self.config['host']
        self.consumer: KafkaConsumer = None
        self.producer: KafkaProducer = None

    def send_package_request(self, request: CBPackageRequest) -> None:
        """
        Send a package build request

        Send a message conforming to the package_request_schema
        to kafka. The information for the message is taken from
        an instance of CBPackageRequest

        :param CBPackageRequest request: Instance of CBPackageRequest
        """
        self._create_producer()
        message = yaml.dump(request.get_data()).encode()
        self.producer.send(
            'cb-request', message
        ).add_callback(self._on_send_success).add_errback(self._on_send_error)
        self.producer.flush()

    def acknowledge(self) -> None:
        """
        Acknowledge message so we don't get it again
        """
        if self.consumer:
            self.consumer.commit()

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
        self.log.info(
            f'Message successfully sent to: {record_metadata.topic}'
        )

    def _on_send_error(self, exception):
        """
        Callback for error sending of a message
        """
        self.log.error(
            f'Message failed with: {exception}'
        )

    def _create_producer(self) -> None:
        """
        Create a KafkaProducer
        """
        if not self.producer:
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=self.kafka_host
                )
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
                self.consumer = KafkaConsumer(
                    topic,
                    auto_offset_reset='earliest',
                    enable_auto_commit=False,
                    max_poll_records=1,
                    bootstrap_servers=self.kafka_host,
                    client_id=client,
                    group_id=group
                )
            except Exception as issue:
                raise CBKafkaConsumerException(
                    f'Creating kafka consumer failed with: {issue!r}'
                )