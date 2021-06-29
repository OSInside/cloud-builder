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
from cerberus import Validator
from typing import List
from kafka import KafkaConsumer
from kafka import KafkaProducer
from cloud_builder.package_request import CBPackageRequest
from cloud_builder.package_request_schema import package_request_schema
from cloud_builder.cloud_logger import CBCloudLogger
from cloud_builder.exceptions import (
    CBConfigFileNotFoundError,
    CBKafkaProducerException,
    CBKafkaConsumerException
)


class CBKafka:
    """
    Implements Kafka message handling in the context of Cloud Builder

    Messages send by an instance of CBKafka uses
    transport schemas which has to be valid against the
    data read from Kafka
    """
    def __init__(self, config_file: str) -> None:
        """
        Create a new instance of CBKafka

        :param str config_file: Kafka credentials file

            .. code:: yaml

                host: kafka-example.com:12345
        """
        try:
            with open(config_file, 'r') as config:
                self.kafka_config = yaml.safe_load(config)
        except Exception as issue:
            raise CBConfigFileNotFoundError(issue)
        self.log = CBCloudLogger('CBKafka', '(system)')
        self.kafka_host = self.kafka_config['host']
        self.consumer: KafkaConsumer = None
        self.producer: KafkaProducer = None

    def send_request(self, request: CBPackageRequest) -> None:
        """
        Send a message conforming to the package_request_schema to kafka
        The information for the message is taken from an instance
        of CBPackageRequest

        :param CBPackageRequest request: Instance of CBPackageRequest
        """
        self._create_producer()
        message = yaml.dump(request.get_data()).encode()
        self.producer.send(
            'cb-request', message
        ).add_callback(self._on_send_success).add_errback(self._on_send_error)
        # We want this message to go out now
        self.producer.flush()

    def read_request(
        self, client: str = 'cb-client', group: str = 'cb-group',
        timeout_ms: int = 1000
    ) -> List:
        """
        Read messages from kafka. The message has to be valid
        YAML and has to follow the package_request_schema in order to
        be processed in the context of the Cloud Builder project

        :param str client: kafka consumer client name
        :param str group: kafka consumer group name
        :param int timeout_ms: read timeout in ms

        :return: list of dicts from yaml.safe_load

        :return: list of yaml dicts validated against package_request_schema

        :rtype: list
        """
        request_list = []
        for message in self.read('cb-request', client, group, timeout_ms):
            try:
                message_as_yaml = yaml.safe_load(message.value)
                validator = Validator(package_request_schema)
                validator.validate(
                    message_as_yaml, package_request_schema
                )
                if validator.errors:
                    self.log.error(
                        'Validation for "{0}" failed with: {1}'.format(
                            message_as_yaml, validator.errors
                        )
                    )
                else:
                    request_list.append(message_as_yaml)
            except yaml.YAMLError as issue:
                self.log.error(
                    'YAML load for "{0}" failed with: "{1}"'.format(
                        message, issue
                    )
                )
        return request_list

    def acknowledge(self) -> None:
        """
        Acknowledge message so we don't get it again for
        this client/group
        """
        if self.consumer:
            self.consumer.commit()

    def close(self) -> None:
        """
        Close consumer for this client/group
        """
        if self.consumer:
            self.consumer.close()

    def read(
        self, topic: str, client: str, group: str, timeout_ms: int
    ) -> List:
        """
        Read messages from kafka.

        :param str topic: kafka topic
        :param str client: kafka consumer client name
        :param str group: kafka consumer group name
        :param int timeout_ms: read timeout in ms

        :return: list of Kafka poll results

        :rtype: List
        """
        message_data = []
        self._create_consumer(topic, client, group)
        # Call poll twice. First call will just assign partitions
        # for the consumer without content.
        for _ in range(2):
            raw_messages = self.consumer.poll(timeout_ms=timeout_ms)
            for topic_partition, message_list in raw_messages.items():
                for message in message_list:
                    message_data.append(message)
        return message_data

    def _on_send_success(self, record_metadata):
        self.log.info(
            f'Message successfully sent to: {record_metadata.topic}'
        )

    def _on_send_error(self, exception):
        self.log.error(
            f'Message failed with: {exception}'
        )

    def _create_producer(self) -> KafkaProducer:
        """
        Create a KafkaProducer

        :rtype: KafkaProducer
        """
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
    ) -> KafkaConsumer:
        """
        Create a KafkaConsumer

        :param str topic: kafka topic
        :param str client: kafka consumer client name
        :param str group: kafka consumer group name

        :rtype: KafkaConsumer
        """
        try:
            self.consumer = KafkaConsumer(
                topic,
                auto_offset_reset='earliest',
                bootstrap_servers=self.kafka_host,
                client_id=client,
                group_id=group
            )
        except Exception as issue:
            raise CBKafkaConsumerException(
                f'Creating kafka consumer failed with: {issue!r}'
            )
