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
from typing import (
    Dict, List
)
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
        self.producer.flush()

    def validate_request(self, message: str) -> Dict:
        """
        validate message against transport schema

        invalid messages will be auto committed such that they
        don't appear again

        :param str message: value from consumer poll

        :return: yaml formatted dict

        :rtype: str
        """
        message_as_yaml = {}
        try:
            message_as_yaml = yaml.safe_load(message)
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
                self.acknowledge()
        except yaml.YAMLError as issue:
            self.log.error(
                'YAML load for "{0}" failed with: "{1}"'.format(
                    message, issue
                )
            )
            self.acknowledge()
        return message_as_yaml

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
        self, topic: str, client: str = 'cb-client',
        group: str = 'cb-group', timeout_ms: int = 1000
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

    def _create_producer(self) -> None:
        """
        Create a KafkaProducer

        :rtype: KafkaProducer
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

        :rtype: KafkaConsumer
        """
        if not self.consumer:
            try:
                self.consumer = KafkaConsumer(
                    topic,
                    auto_offset_reset='earliest',
                    enable_auto_commit=False,
                    bootstrap_servers=self.kafka_host,
                    client_id=client,
                    group_id=group
                )
            except Exception as issue:
                raise CBKafkaConsumerException(
                    f'Creating kafka consumer failed with: {issue!r}'
                )
