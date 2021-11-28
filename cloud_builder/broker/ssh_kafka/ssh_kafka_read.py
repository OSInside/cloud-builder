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
usage: ssh_kafka_read -h | --help
       ssh_kafka_read --topic=<name> --group=<name>
           [--client=<name>]
           [--timeout=<mseconds>]

options:
    --topic=<name>
        topic to read from

    --client=<name>
        client name, defaults to: 'cb-client'

    --timeout=<mseconds>
        read timeout in mseconds, default: 1000ms
"""
import yaml
import time
from docopt import docopt

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
        version='CB (ssh_kafka_read) version ' + __version__,
        options_first=True
    )
    broker = CBMessageBroker.new(
        'kafka', config_file=Defaults.get_broker_config()
    )
    timeout_sec = int(args['--timeout'] or 1000) / 1000
    try:
        timeout_loop_start = time.time()
        result_messages = []
        while time.time() < timeout_loop_start + timeout_sec + 1:
            messages = broker.read(
                topic=args['--topic'],
                group=args['--group'],
                client=args['--client'] or 'cb-client',
                timeout_ms=timeout_sec * 1000
            )
            for message in messages:
                result_messages.append(message.value.decode())
        print(yaml.dump(result_messages))
    except Exception as issue:
        raise CBParameterError(issue)
    finally:
        broker.acknowledge()
        broker.close()
