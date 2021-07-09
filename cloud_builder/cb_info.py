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
usage: cb-info -h | --help
       cb-info
           [--update-interval=<time_sec>]

options:
    --update-interval=<time_sec>
        Optional update interval for the lookup
        Default is 30sec

"""
import os
import glob
import psutil
from typing import Any
from datetime import datetime
from docopt import docopt
from cloud_builder.version import __version__
from cloud_builder.exceptions import exception_handler
from cloud_builder.message_broker import CBMessageBroker
from cloud_builder.defaults import Defaults
from kiwi.privileges import Privileges


@exception_handler
def main() -> None:
    """
    cb-info - lookup package information. The package
    builds on a runner contains a number of files like
    the following example:

    /var/tmp/CB/
           ├── package.log
           ├── package.pid
           ├── package.sh
           ├── package@DIST.ARCH/
           ├── package@DIST.ARCH.build.log
           ├── package@DIST.ARCH.prepare.log
           ├── package@DIST.ARCH.solver.yml
           └── package@DIST.ARCH.result.yml

    The local file information is used to construct
    a response record with information about the
    package build:
    """
    args = docopt(
        __doc__,
        version='CB (info) version ' + __version__,
        options_first=True
    )

    Privileges.check_for_root_permissions()

    broker = CBMessageBroker.new(
        'kafka', config_file=Defaults.get_kafka_config()
    )

    # In the code reading from the info queue use the
    # pub/sub method and assign the unique request_id as
    # consumer group name
    # https://stackoverflow.com/questions/23136500/how-kafka-broadcast-to-many-consumer-groups

    print(args)
    lookup('xclock', 'uuid', broker)


def lookup(package: str, request_id: str, broker: Any):
    build_result_file_glob_pattern = os.sep.join(
        [Defaults.get_runner_package_root(), f'{package}*.result.yml']
    )
    build_pid_file = os.sep.join(
        [Defaults.get_runner_package_root(), f'{package}.pid']
    )
    for package_result_file in glob.iglob(build_result_file_glob_pattern):
        utc_mod_time = get_result_modification_time(package_result_file)
        (dist, arch) = package_result_file.replace(
            Defaults.get_runner_package_root(), ''
        ).split('@')[1].split('.')[:2]
        with open(package_result_file) as result_file:
            result = broker.validate_package_response(result_file.read())
            source_ip = result['identity'].split(':')[1]
            binary_packages = result['binary_packages']
            log_file = result['log_file']
            solver_file = result['solver_file']

            print(request_id)
            print(package)
            print(source_ip)
            print(binary_packages)
            print(log_file)
            print(solver_file)
            print(utc_mod_time)
            print(dist)
            print(arch)
            print(
                get_package_status(build_pid_file, result['response_code'])
            )


def get_result_modification_time(filename: str) -> datetime:
    return datetime.utcfromtimestamp(
        os.path.getmtime(filename)
    )


def get_package_status(pidfile: str, response_code: str) -> str:
    status_flags = Defaults.get_status_flags()
    with open(pidfile) as pid_fd:
        build_pid = int(pid_fd.read())
        if psutil.pid_exists(build_pid):
            response_code = status_flags.package_build_running
    if response_code == status_flags.package_build_succeeded:
        return status_flags.package_build_succeeded
    elif response_code == status_flags.package_build_failed:
        return status_flags.package_build_failed
    elif response_code == status_flags.package_build_running:
        return status_flags.package_build_running
    else:
        return 'unknown'
