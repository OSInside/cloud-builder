from mock import patch

from cloud_builder.build_request.build_request import CBBuildRequest


class TestCBBuildRequest:
    def setup(self):
        self.request = CBBuildRequest()

    @patch('cloud_builder.build_request.build_request.CBIdentity')
    def test_set_package_build_request(self, mock_CBIdentity):
        self.request.set_package_build_request(
            'vim', 'x86_64', 'TW', 'runner_group', 'action'
        )
        assert self.request.get_data() == {
            'package': {
                'arch': 'x86_64',
                'dist': 'TW'
            },
            'action': 'action',
            'project': 'vim',
            'runner_group': 'runner_group',
            'request_id': mock_CBIdentity.get_request_id.return_value,
            'schema_version': 0.2
        }

    @patch('cloud_builder.build_request.build_request.CBIdentity')
    def test_set_image_build_request(self, mock_CBIdentity):
        self.request.set_image_build_request(
            'myimage', 'x86_64', 'selection', 'runner_group', 'action'
        )
        assert self.request.get_data() == {
            'image': {
                'arch': 'x86_64',
                'selection': 'selection'
            },
            'action': 'action',
            'project': 'myimage',
            'runner_group': 'runner_group',
            'request_id': mock_CBIdentity.get_request_id.return_value,
            'schema_version': 0.2
        }
