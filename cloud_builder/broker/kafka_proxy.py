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
import os
import logging
import paramiko
from typing import (
    List, NamedTuple
)
import yaml

from cloud_builder.defaults import Defaults
from cloud_builder.build_request.build_request import CBBuildRequest
from cloud_builder.info_request.info_request import CBInfoRequest
from cloud_builder.response.response import CBResponse
from cloud_builder.info_response.info_response import CBInfoResponse
from cloud_builder.broker.base import CBMessageBrokerBase

from cloud_builder.exceptions import (
    CBParameterError,
    CBSSHConnectionError
)

fake_kafka_message = NamedTuple(
    'fake_kafka_message', [
        ('value', bytes)
    ]
)

log = logging.getLogger('cloud_builder')


class CBMessageBrokerSSHProxyKafka(CBMessageBrokerBase):
    """
    Interface for kafka message handling through SSH
    in the context of Cloud Builder
    """
    def post_init(self) -> None:
        """
        Create a new instance of CBMessageBrokerSSHProxyKafka
        """
        self.config = self.custom_args

        self.pkey_file = self.config['cluster'].get('ssh_pkey_file') or 'none'
        self.user = self.config['cluster'].get('ssh_user') or ''
        self.host = self.config['cluster'].get('controlplane') or ''
        if not os.path.isfile(self.pkey_file):
            raise CBParameterError(
                f'SSH pkey file not found: {self.pkey_file}'
            )
        if not self.user or not self.host:
            raise CBParameterError(
                f'SSH endpoint invalid: {self.user}@{self.host}'
            )
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(
            paramiko.AutoAddPolicy()
        )
        try:
            self.ssh.connect(
                key_filename=self.pkey_file,
                hostname=self.host,
                username=self.user,
                look_for_keys=False,
                allow_agent=False
            )
        except Exception as issue:
            raise CBSSHConnectionError(issue)

    def send_build_request(self, request: CBBuildRequest) -> None:
        """
        Send a package/image build request

        Send a message conforming to the build_request_schema
        to kafka. The information for the message is taken from
        an instance of CBBuildRequest

        :param CBBuildRequest request: Instance of CBBuildRequest
        """
        self._run_ssh_kafka_write(
            request.get_data()['runner_group'],
            yaml.dump(request.get_data()).encode()
        )

    def send_info_request(self, request: CBInfoRequest) -> None:
        """
        Send a info request

        Send a message conforming to the info_request_schema
        to kafka. The information for the message is taken from
        an instance of CBInfoRequest

        :param CBInfoRequest request: Instance of CBInfoRequest
        """
        self._run_ssh_kafka_write(
            Defaults.get_info_request_queue_name(),
            yaml.dump(request.get_data()).encode()
        )

    def send_response(self, response: CBResponse) -> None:
        """
        Send a response

        Send a message conforming to the response_schema
        to kafka. The information for the message is taken from
        an instance of CBResponse

        :param CBResponse response: Instance of CBResponse
        """
        self._run_ssh_kafka_write(
            Defaults.get_response_queue_name(),
            yaml.dump(response.get_data()).encode()
        )

    def send_info_response(self, response: CBInfoResponse) -> None:
        """
        Send a info response

        Send a message conforming to the info_response_schema
        to kafka. The information for the message is taken from
        an instance of CBInfoResponse

        :param CBInfoResponse response: Instance of CBInfoResponse
        """
        self._run_ssh_kafka_write(
            Defaults.get_info_response_queue_name(),
            yaml.dump(response.get_data()).encode()
        )

    def acknowledge(self) -> None:
        """
        Acknowledge message so we don't get it again

        There is no way for us to acknowledge the message when
        redirecting the kafka consumer to another host.
        """
        pass

    def get_runner_group(self) -> str:
        """
        Return runner identification for package build requests.
        In kafka this is the topic name of the request queue.
        This information is usually taken from the broker
        configuration. In Proxy mode there is no broker setup
        on the calling host. Thus this method must not be
        called and raises with an error intentionally

        :return: raises

        :rtype: str
        """
        raise NotImplementedError

    def close(self) -> None:
        """
        Close connection to message system

        There is no way for us to close the connection when
        redirecting the kafka connection to another host. Thus
        the connection close happens in ssh_kafka_read and
        ssh_kafka_write
        """
        pass

    def read(
        self, topic: str, client: str = 'cb-client',
        group: str = 'cb-group', timeout_ms: int = 1000
    ) -> List[fake_kafka_message]:
        """
        Read messages from message system.

        :param str topic: kafka topic
        :param str client: kafka consumer client name
        :param str group: kafka consumer group name
        :param int timeout_ms: read timeout in ms

        :return: list of fake_kafka_message poll results

        :rtype: List
        """
        (stdin, stdout, stderr) = self.ssh.exec_command(
            'ssh_kafka_read {0} {1} {2} {3}'.format(
                f'--topic {topic}',
                f'--group {group}',
                f'--client {client}',
                f'--timeout {timeout_ms}'
            )
        )
        result = []
        for message in yaml.safe_load(stdout.read()):
            result.append(
                fake_kafka_message(value=message.encode())
            )
        return result

    def _run_ssh_kafka_write(self, topic: str, yaml_raw: bytes) -> None:
        (stdin, stdout, stderr) = self.ssh.exec_command(
            f'echo "{yaml_raw.decode()}" | ssh_kafka_write --topic {topic}'
        )
        issue = stderr.read()
        if issue:
            self._on_send_error(issue)
        else:
            self._on_send_success(topic)

    def _on_send_success(self, topic):
        """
        Callback for successful sending of a message
        """
        log.debug(
            f'Message successfully sent to: {topic}'
        )

    def _on_send_error(self, message):
        """
        Callback for error sending of a message
        """
        log.debug(
            f'Message failed with: {message}'
        )

    def __del__(self):
        self.ssh.close()
