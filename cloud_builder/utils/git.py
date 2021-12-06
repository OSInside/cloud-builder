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
from kiwi.command import Command
from kiwi.path import Path
from typing import List


class CBGit:
    def __init__(self, git_clone_uri: str = '', checkout_path: str = '.'):
        self.git_clone_uri = git_clone_uri
        self.checkout_path = checkout_path

    def clone(self, branch: str = '') -> None:
        if self.git_clone_uri:
            Path.wipe(self.checkout_path)
            Command.run(
                ['git', 'clone', self.git_clone_uri, self.checkout_path]
            )
            if branch:
                Command.run(
                    ['git', '-C', self.checkout_path, 'checkout', branch]
                )

    def pull(self) -> None:
        Command.run(
            ['git', '-C', self.checkout_path, 'pull']
        )

    def fetch(self) -> None:
        Command.run(
            ['git', '-C', self.checkout_path, 'fetch', '--all']
        )

    def get_changed_files(self) -> List[str]:
        git_changes = Command.run(
            [
                'git', '-C', self.checkout_path,
                'diff', '--name-only', 'origin/master'
            ]
        )
        changed_files = []
        if git_changes.output:
            changed_files = git_changes.output.strip().split(os.linesep)
        return changed_files
