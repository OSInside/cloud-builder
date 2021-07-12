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
from typing import Dict
from cloud_builder.identity import CBIdentity


class CBInfoRequest:
    """
    Implement creation of info request schema valid data dict
    """
    def __init__(self) -> None:
        self.info_request_dict: Dict = {}
        self.info_request_schema_version = 0.1

    def set_info_request(self, package: str, arch: str, dist: str) -> None:
        self.info_request_dict = {
            'schema_version': self.info_request_schema_version,
            'request_id': CBIdentity.get_request_id(),
            'package': package,
            'arch': arch,
            'dist': dist
        }

    def get_data(self) -> Dict:
        return self.info_request_dict
