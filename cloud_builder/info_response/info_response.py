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
from typing import (
    Dict, List
)


class CBInfoResponse:
    """
    Implement creation of response info schema valid data dict
    """
    def __init__(self, request_id: str, identity: str) -> None:
        self.info_schema_version = 0.1
        self.info_response_dict: Dict = {
            'schema_version': self.info_schema_version,
            'identity': identity,
            'request_id': request_id,
            'architectures': []
        }

    def set_info_response(
        self, package: str, source_ip: str, is_running: bool,
        arch: str, dist: str, binary_packages: List[str] = [],
        log_file: str = 'unknown', solver_file: str = 'unknown',
        utc_modification_time: str = 'unknown', build_status: str = 'unknown'
    ) -> None:
        self.info_response_dict = {
            **self.info_response_dict,
            'package': package,
            'source_ip': source_ip,
            'is_running': is_running,
            'arch': arch,
            'dist': dist,
            'binary_packages': binary_packages,
            'log_file': log_file,
            'solver_file': solver_file,
            'utc_modification_time': utc_modification_time,
            'build_status': build_status
        }

    def set_info_response_result(
        self, binary_packages: List[str], log_file: str,
        solver_file: str, utc_modification_time: str,
        build_status: str
    ) -> None:
        self.info_response_dict['binary_packages'] = binary_packages
        self.info_response_dict['log_file'] = log_file
        self.info_response_dict['solver_file'] = solver_file
        self.info_response_dict['utc_modification_time'] = utc_modification_time
        self.info_response_dict['build_status'] = build_status

    def get_data(self) -> Dict:
        return self.info_response_dict
