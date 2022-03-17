from mock import patch

from cloud_builder.info_request.info_request import CBInfoRequest


class TestCBInfoRequest:
    def setup(self):
        self.info_request = CBInfoRequest()

    def setup_method(self, cls):
        self.setup()

    @patch('cloud_builder.info_request.info_request.CBIdentity')
    def test_set_package_info_request(self, mock_CBIdentity):
        self.info_request.set_package_info_request('vim', 'x86_64', 'TW')
        assert self.info_request.get_data() == {
            'project': 'vim',
            'package': {
                'arch': 'x86_64',
                'dist': 'TW'
            },
            'request_id': mock_CBIdentity.get_request_id.return_value,
            'schema_version': 0.2
        }

    @patch('cloud_builder.info_request.info_request.CBIdentity')
    def test_set_image_info_request(self, mock_CBIdentity):
        self.info_request.set_image_info_request('myimage', 'x86_64', 'selection')
        assert self.info_request.get_data() == {
            'project': 'myimage',
            'image': {
                'arch': 'x86_64',
                'selection': 'selection'
            },
            'request_id': mock_CBIdentity.get_request_id.return_value,
            'schema_version': 0.2
        }
