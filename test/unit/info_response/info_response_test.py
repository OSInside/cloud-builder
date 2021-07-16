from cloud_builder.info_response.info_response import CBInfoResponse


class TestCBInfoResponse:
    def setup(self):
        self.info_response = CBInfoResponse('uuid', 'identity')

    def test_set_info_response(self):
        self.info_response.set_info_response(
            'package', 'source_ip', True, 'x86_64', 'TW'
        )
        assert self.info_response.get_data() == {
            **self.info_response.info_response_dict,
            'package': 'package',
            'source_ip': 'source_ip',
            'is_running': True,
            'arch': 'x86_64',
            'dist': 'TW',
            'binary_packages': [],
            'prepare_log_file': 'unknown',
            'log_file': 'unknown',
            'solver_file': 'unknown',
            'utc_modification_time': 'unknown',
            'build_status': 'unknown'
        }

    def test_set_info_response_result(self):
        self.info_response.set_info_response(
            'package', 'source_ip', True, 'x86_64', 'TW'
        )
        self.info_response.set_info_response_result(
            ['binary'], 'prepare_log_file', 'log_file', 'solver_file', 'timestamp', 'build_status'
        )
        assert self.info_response.get_data() == {
            **self.info_response.info_response_dict,
            'package': 'package',
            'source_ip': 'source_ip',
            'is_running': True,
            'arch': 'x86_64',
            'dist': 'TW',
            'binary_packages': ['binary'],
            'prepare_log_file': 'prepare_log_file',
            'log_file': 'log_file',
            'solver_file': 'solver_file',
            'utc_modification_time': 'timestamp',
            'build_status': 'build_status'
        }
