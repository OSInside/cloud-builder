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
from cerberus import Validator
from typing import (
    List, NamedTuple
)
import yaml
from kafka import KafkaConsumer
from kafka import KafkaProducer
from cloud_builder.request import CBRequest
from cloud_builder.request_schema import request_schema
from cloud_builder.logger import CBLogger
from cloud_builder.exceptions import (
    CBConfigFileNotFoundError,
    CBKafkaProducerException,
    CBKafkaConsumerException
)

kafka_read_type = NamedTuple(
    'kafka_read_type', [
        ('consumer', KafkaConsumer),
        ('message_list', List)
    ]
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
                topic: cb-request
        """
        try:
            with open(config_file, 'r') as config:
                self.kafka_config = yaml.safe_load(config)
        except Exception as issue:
            raise CBConfigFileNotFoundError(issue)
        self.kafka_host = self.kafka_config['host']
        self.kafka_topic = self.kafka_config['topic']

    def send_request(self, request: CBRequest) -> None:
        """
        Send a message conforming to the request_schema to kafka
        The information for the message is taken from an instance
        of CBRequest

        :param CBRequest request: Instance of CBRequest
        """
        message_broker = self.__create_broker()
        message_broker.send(
            self.kafka_topic, yaml.dump(request.get_data()).encode()
        )
        # We want this message to go out now
        message_broker.flush()

    def read_request(self, timeout_ms=1000) -> kafka_read_type:
        """
        Read messages from kafka. The message has to be valid
        YAML and has to follow the request_schema in order to
        be processed in the context of the Cloud Builder project

        :param int timeout_ms: read timeout in ms

        :return: list of dicts from yaml.safe_load

        :rtype: list
        """
        request_list = []
        log = CBLogger.get_logger()
        kafka = self.read(timeout_ms)
        for message in kafka.message_list:
            try:
                message_as_yaml = yaml.safe_load(message.value)
                validator = Validator(request_schema)
                validator.validate(
                    message_as_yaml, request_schema
                )
                if validator.errors:
                    log.error(
                        'Validation for "{0}" failed with: {1}'.format(
                            message_as_yaml, validator.errors
                        )
                    )
                else:
                    request_list.append(message_as_yaml)
            except yaml.YAMLError as issue:
                log.error(
                    f'YAML load for {message!r} failed with: {issue!r}'
                )
        return kafka_read_type(
            consumer=kafka.consumer,
            message_list=request_list
        )

    def acknowledge(self, consumer: KafkaConsumer) -> None:
        """
        Acknowledge message so we don't get it again for
        this client/group

        :param KafkaConsumer consumer: Kafka Consumer object
        """
        consumer.commit()

    def read(self, timeout_ms=1000) -> kafka_read_type:
        """
        Read messages from kafka.

        :param int timeout_ms: read timeout in ms

        :return: kafka_read_type

        :rtype: Tuple
        """
        message_data = []
        message_consumer = self.__create_consumer()
        # Call poll twice. First call will just assign partitions
        # for the consumer without content.
        for _ in range(2):
            raw_messages = message_consumer.poll(timeout_ms=timeout_ms)
            for topic_partition, message_list in raw_messages.items():
                for message in message_list:
                    message_data.append(message)
        return kafka_read_type(
            consumer=message_consumer,
            message_list=message_data
        )

    def __create_broker(self) -> KafkaProducer:
        """
        Create a KafkaProducer

        :rtype: KafkaProducer
        """
        try:
            return KafkaProducer(
                bootstrap_servers=self.kafka_host
            )
        except Exception as issue:
            raise CBKafkaProducerException(
                f'Creating kafka producer failed with: {issue!r}'
            )

    def __create_consumer(
        self, client='cb-client', group='cb-group'
    ) -> KafkaConsumer:
        """
        Create a KafkaConsumer

        :rtype: KafkaConsumer
        """
        try:
            return KafkaConsumer(
                self.kafka_topic,
                auto_offset_reset='earliest',
                bootstrap_servers=self.kafka_host,
                client_id=client,
                group_id=group
            )
        except Exception as issue:
            raise CBKafkaConsumerException(
                f'Creating kafka consumer failed with: {issue!r}'
            )
