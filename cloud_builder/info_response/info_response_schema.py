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
info_response_schema = {
    'schema_version': {
        'required': True,
        'type': 'number',
        'nullable': False
    },
    'identity': {
        'required': True,
        'type': 'string',
        'nullable': False
    },
    'request_id': {
        'required': True,
        'type': 'string',
        'nullable': False
    },
    'package': {
        'required': True,
        'type': 'string',
        'nullable': False
    },
    'source_ip': {
        'required': True,
        'type': 'string',
        'nullable': False
    },
    'is_running': {
        'required': True,
        'type': 'bool'
    },
    'arch': {
        'required': True,
        'type': 'string',
        'nullable': False
    },
    'dist': {
        'required': True,
        'type': 'string',
        'nullable': False
    },
    'binary_packages': {
        'required': True,
        'type': 'list',
        'nullable': True
    },
    'log_file': {
        'required': True,
        'type': 'string',
        'nullable': False
    },
    'solver_file': {
        'required': True,
        'type': 'string',
        'nullable': False
    },
    'utc_modification_time': {
        'required': True,
        'type': 'string',
        'nullable': False
    },
    'build_status': {
        'required': True,
        'type': 'string',
        'nullable': False
    }
}
