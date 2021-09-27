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


class CBBuildRequest:
    """
    Implement creation of request schema valid data dict
    """
    def __init__(self) -> None:
        self.build_request_dict: Dict = {}
        self.build_request_schema_version = 0.2

    def set_package_build_request(
        self, package: str, arch: str, dist: str, runner_group: str,
        action: str
    ) -> None:
        self._set_base_request(package, runner_group, action)
        self.build_request_dict['package'] = {
            'arch': arch,
            'dist': dist
        }

    def set_image_build_request(
        self, image: str, arch: str, selection: str, runner_group: str,
        action: str
    ) -> None:
        self._set_base_request(image, runner_group, action)
        self.build_request_dict['image'] = {
            'arch': arch,
            'selection': selection
        }

    def get_data(self) -> Dict:
        return self.build_request_dict

    def _set_base_request(
        self, package: str, runner_group: str, action: str
    ) -> None:
        self.build_request_dict = {
            'schema_version': self.build_request_schema_version,
            'request_id': CBIdentity.get_request_id(),
            'project': package,
            'runner_group': runner_group,
            'action': action
        }
