from cloud_builder.info_response import CBInfoResponse


class TestCBInfoResponse:
    def setup(self):
        self.info_response = CBInfoResponse('uuid', 'identity')

    def test_set_info_response(self):
        self.info_response.set_info_response('package', 'source_ip')
        assert self.info_response.get_data() == {
            **self.info_response.info_response_dict,
            'package': 'package',
            'source_ip': 'source_ip'
        }

    def test_add_info_response_architecture(self):
        self.info_response.add_info_response_architecture('arch')
        assert self.info_response.get_data()['architectures'] == [
            {
                'arch': 'arch',
                'distributions': []
            }
        ]

    def test_add_info_response_distribution_for_arch(self):
        self.info_response.add_info_response_architecture('arch')
        self.info_response.add_info_response_distribution_for_arch(
            'arch', 'dist', [], 'log_file', 'solver_file',
            'utc_modification_time', 'build_status'
        )
        assert self.info_response.get_data()['architectures'] == [
            {
                'arch': 'arch',
                'distributions': [
                    {
                        'dist': 'dist',
                        'binary_packages': [],
                        'log_file': 'log_file',
                        'solver_file': 'solver_file',
                        'utc_modification_time': 'utc_modification_time',
                        'build_status': 'build_status'
                    }
                ]
            }
        ]
