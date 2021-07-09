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


class CBInfoRequest:
    """
    Implement creation of info request schema valid data dict
    """
    def __init__(self, request_id: str, identity: str) -> None:
        self.info_schema_version = 0.1
        self.info_request_dict: Dict = {
            'schema_version': self.info_schema_version,
            'identity': identity,
            'request_id': request_id
        }

    def set_info_request(self, package: str) -> None:
        self.info_request_dict = {
            **self.info_request_dict,
            'package': package
        }

    def get_data(self) -> Dict:
        return self.info_request_dict
