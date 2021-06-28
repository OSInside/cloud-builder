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
import urllib.request


class CBIdentity:
    """
    Implements ID schema
    """
    @staticmethod
    def get_id():
        return f'{CBIdentity.get_external_ip()}:{os.getpid()}'

    @staticmethod
    def get_external_ip():
        return urllib.request.urlopen(
            'https://api.ipify.org'
        ).read().decode()
