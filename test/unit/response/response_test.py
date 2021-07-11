from cloud_builder.response.response import CBResponse


class TestCBResponse:
    def setup(self):
        self.response = CBResponse('uuid', 'identity')

    def test_set_package_build_response(self):
        self.response.set_package_build_response(
            'message', 'response_code', 'package', 'log_file',
            'solver_file', [], 0
        )
        assert self.response.get_data() == {
            **self.response.response_dict,
            'message': 'message',
            'response_code': 'response_code',
            'package': 'package',
            'log_file': 'log_file',
            'solver_file': 'solver_file',
            'binary_packages': [],
            'exit_code': 0
        }

    def test_set_package_buildroot_response(self):
        self.response.set_package_buildroot_response(
            'message', 'response_code', 'package', 'log_file',
            'solver_file', 'build_root', 0
        )
        assert self.response.get_data() == {
            **self.response.response_dict,
            'message': 'message',
            'response_code': 'response_code',
            'package': 'package',
            'log_file': 'log_file',
            'solver_file': 'solver_file',
            'build_root': 'build_root',
            'exit_code': 0
        }

    def test_set_package_update_request_response(self):
        self.response.set_package_update_request_response(
            'message', 'response_code', 'package', 'arch', 'dist'
        )
        assert self.response.get_data() == {
            **self.response.response_dict,
            'message': 'message',
            'response_code': 'response_code',
            'package': 'package',
            'arch': 'arch',
            'dist': 'dist'
        }

    def test_set_package_build_scheduled_response(self):
        self.response.set_package_build_scheduled_response(
            'message', 'response_code', 'package', 'arch', 'dist'
        )
        assert self.response.get_data() == {
            **self.response.response_dict,
            'message': 'message',
            'response_code': 'response_code',
            'package': 'package',
            'arch': 'arch',
            'dist': 'dist'
        }

    def test_set_buildhost_arch_incompatible_response(self):
        self.response.set_buildhost_arch_incompatible_response(
            'message', 'response_code', 'package'
        )
        assert self.response.get_data() == {
            **self.response.response_dict,
            'message': 'message',
            'response_code': 'response_code',
            'package': 'package'
        }

    def test_set_package_jobs_reset_response(self):
        self.response.set_package_jobs_reset_response(
            'message', 'response_code', 'package', 'arch', 'dist'
        )
        assert self.response.get_data() == {
            **self.response.response_dict,
            'message': 'message',
            'response_code': 'response_code',
            'package': 'package',
            'arch': 'arch',
            'dist': 'dist'
        }

    def test_set_package_not_existing_response(self):
        self.response.set_package_not_existing_response(
            'message', 'response_code', 'package'
        )
        assert self.response.get_data() == {
            **self.response.response_dict,
            'message': 'message',
            'response_code': 'response_code',
            'package': 'package'
        }

    def test_set_package_invalid_metadata_response(self):
        self.response.set_package_invalid_metadata_response(
            'message', 'response_code', 'package'
        )
        assert self.response.get_data() == {
            **self.response.response_dict,
            'message': 'message',
            'response_code': 'response_code',
            'package': 'package'
        }
