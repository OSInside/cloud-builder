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
from cloud_builder.defaults import Defaults


class CBRequest:
    """
    Implement creation of request schema valid data dict
    """
    def __init__(self) -> None:
        self.request_dict: Dict = {}
        self.request_schema_version = 0.1

    def set_package_source_change_request(self, package: str) -> None:
        self.request_dict = {
            'schema_version': self.request_schema_version,
            'package': package,
            'action': Defaults.get_status_flags().package_changed
        }

    def get_data(self) -> Dict:
        return self.request_dict
