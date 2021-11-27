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
from typing import (
    Optional, NamedTuple
)

from kiwi.path import Path

repo_metadata = NamedTuple(
    'repo_metadata', [
        ('repo_type', str),
        ('repo_file', str),
        ('repo_path', str)
    ]
)


class CBRepository:
    def __init__(self, binary_file: str):
        self.binary_file = binary_file

    def get_repo_type(self) -> Optional[str]:
        """
        Lookup repo type according to the package extension of
        the given binary file name
        """
        if self.binary_file.endswith('.rpm'):
            return 'rpm'
        return None

    def get_repo_meta(self, base_repo_path: str) -> repo_metadata:
        """
        Check given binary file name and apply repo
        schema if known
        """
        repo_path = 'unknown'
        repo_type = self.get_repo_type() or 'unknown'
        if self.binary_file.endswith('.src.rpm'):
            repo_path = f'{base_repo_path}/src'
        elif self.binary_file.endswith('.noarch.rpm'):
            repo_path = f'{base_repo_path}/noarch'
        elif self.binary_file.endswith('.rpm'):
            arch = self.binary_file.split('.')[-2]
            repo_path = f'{base_repo_path}/{arch}'
        else:
            # Don't know about this binary type...
            return repo_metadata(
                repo_type=repo_type,
                repo_path=repo_path,
                repo_file=os.sep.join(
                    [base_repo_path, os.path.basename(self.binary_file)]
                )
            )
        if not os.path.isdir(repo_path):
            Path.create(repo_path)
        return repo_metadata(
            repo_type=repo_type,
            repo_path=repo_path,
            repo_file=os.sep.join(
                [repo_path, os.path.basename(self.binary_file)]
            )
        )
