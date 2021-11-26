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
"""
usage: ssh_kafka_write -h | --help
       ssh_kafka_write --topic=<name>

options:
    --topic=<name>
        topic to write to
"""
from docopt import docopt
import yaml
import sys

from cloud_builder.version import __version__
from cloud_builder.defaults import Defaults
from cloud_builder.broker import CBMessageBroker

from cloud_builder.exceptions import (
    exception_handler,
    CBParameterError
)


@exception_handler
def main() -> None:
    args = docopt(
        __doc__,
        version='CB (ssh_kafka_write) version ' + __version__,
        options_first=True
    )
    try:
        message = yaml.safe_load(sys.stdin.read())
    except Exception as issue:
        raise CBParameterError(issue)

    broker = CBMessageBroker.new(
        'kafka', config_file=Defaults.get_broker_config()
    )
    try:
        broker._create_producer()
        broker.producer.send(
            args['--topic'], yaml.dump(message).encode()
        ).add_callback(
            broker._on_send_success
        ).add_errback(
            broker._on_send_error
        )
        broker.producer.flush()
    except Exception as issue:
        raise CBParameterError(issue)
    finally:
        broker.close()
