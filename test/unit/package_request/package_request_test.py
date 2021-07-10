from mock import patch

from cloud_builder.package_request.package_request import CBPackageRequest


class TestCBPackageRequest:
    def setup(self):
        self.request = CBPackageRequest()

    @patch('cloud_builder.package_request.package_request.CBIdentity')
    def test_set_package_source_change_request(self, mock_CBIdentity):
        self.request.set_package_source_change_request('vim', 'x86_64')
        assert self.request.get_data() == {
            'action': 'package source changed',
            'arch': 'x86_64',
            'package': 'vim',
            'request_id': mock_CBIdentity.get_request_id.return_value,
            'schema_version': 0.1
        }
