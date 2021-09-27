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


class CBResponse:
    """
    Implement creation of response schema valid data dict
    """
    def __init__(self, request_id: str, identity: str) -> None:
        self.response_schema_version = 0.2
        self.response_dict: Dict = {
            'schema_version': self.response_schema_version,
            'identity': identity,
            'request_id': request_id,
        }

    def set_package_build_response(
        self, message: str, response_code: str, package: str,
        prepare_log_file: str, log_file: str, solver_file: str,
        binary_packages: List[str], exit_code: int
    ) -> None:
        self.response_dict = {
            **self.response_dict,
            'message': message,
            'response_code': response_code,
            'project': package,
            'package': {
                'prepare_log_file': prepare_log_file,
                'log_file': log_file,
                'solver_file': solver_file,
                'binary_packages': binary_packages,
                'exit_code': exit_code
            }
        }

    def set_image_build_response(
        self, message: str, response_code: str, image: str,
        log_file: str, solver_file: str, binary_packages: List[str],
        exit_code: int
    ) -> None:
        self.response_dict = {
            **self.response_dict,
            'message': message,
            'response_code': response_code,
            'project': image,
            'image': {
                'log_file': log_file,
                'solver_file': solver_file,
                'binary_packages': binary_packages,
                'exit_code': exit_code
            }
        }

    def set_package_buildroot_response(
        self, message: str, response_code: str, package: str,
        log_file: str, solver_file: str, build_root: str, exit_code: int
    ) -> None:
        self.response_dict = {
            **self.response_dict,
            'message': message,
            'response_code': response_code,
            'project': package,
            'package_prepare': {
                'prepare_log_file': log_file,
                'solver_file': solver_file,
                'build_root': build_root,
                'exit_code': exit_code
            }
        }

    def set_package_update_request_response(
        self, message: str, response_code: str, package: str,
        arch: str, dist: str
    ) -> None:
        self._set_dist_standard_response(
            message, response_code, package, arch, dist
        )

    def set_image_update_request_response(
        self, message: str, response_code: str, image: str, arch: str,
        selection: str
    ) -> None:
        self._set_selection_standard_response(
            message, response_code, image, arch, selection
        )

    def set_package_build_scheduled_response(
        self, message: str, response_code: str, package: str,
        arch: str, dist: str
    ) -> None:
        self._set_dist_standard_response(
            message, response_code, package, arch, dist
        )

    def set_image_build_scheduled_response(
        self, message: str, response_code: str, image: str, arch: str,
        selection: str
    ) -> None:
        self._set_selection_standard_response(
            message, response_code, image, arch, selection
        )

    def set_package_jobs_reset_response(
        self, message: str, response_code: str, package: str,
        arch: str, dist: str
    ) -> None:
        self._set_dist_standard_response(
            message, response_code, package, arch, dist
        )

    def set_image_jobs_reset_response(
        self, message: str, response_code: str, image: str,
        arch: str, selection: str
    ) -> None:
        self._set_selection_standard_response(
            message, response_code, image, arch, selection
        )

    def set_buildhost_arch_incompatible_response(
        self, message: str, response_code: str, package: str
    ) -> None:
        self._set_standard_response(message, response_code, package)

    def set_project_not_existing_response(
        self, message: str, response_code: str, project: str
    ) -> None:
        self._set_standard_response(message, response_code, project)

    def set_project_invalid_metadata_response(
        self, message: str, response_code: str, project: str
    ) -> None:
        self._set_standard_response(message, response_code, project)

    def set_project_invalid_target_response(
        self, message: str, response_code: str, project: str
    ) -> None:
        self._set_standard_response(message, response_code, project)

    def set_project_metadata_not_existing_response(
        self, message: str, response_code: str, project: str
    ) -> None:
        self._set_standard_response(message, response_code, project)

    def get_data(self) -> Dict:
        return self.response_dict

    def _set_standard_response(
        self, message: str, response_code: str, project: str
    ) -> None:
        self.response_dict = {
            **self.response_dict,
            'message': message,
            'response_code': response_code,
            'project': project
        }

    def _set_selection_standard_response(
        self, message: str, response_code: str, project: str, arch: str,
        selection: str
    ) -> None:
        self.response_dict = {
            **self.response_dict,
            'message': message,
            'response_code': response_code,
            'project': project,
            'target': {
                'arch': arch,
                'selection': selection
            }
        }

    def _set_dist_standard_response(
        self, message: str, response_code: str, project: str,
        arch: str, dist: str
    ) -> None:
        self.response_dict = {
            **self.response_dict,
            'message': message,
            'response_code': response_code,
            'project': project,
            'target': {
                'arch': arch,
                'dist': dist
            }
        }
