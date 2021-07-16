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
cbctl_config_schema = {
    'runner': {
        'required': True,
        'type': 'dict',
        'schema': {
            'ssh_user': {
                'required': True,
                'type': 'string',
                'nullable': False
            },
            'ssh_pkey_file': {
                'required': True,
                'type': 'string',
                'nullable': False
            }
        }
    }
}
