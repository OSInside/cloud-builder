from mock import patch

from cloud_builder.info_request.info_request import CBInfoRequest


class TestCBInfoRequest:
    def setup(self):
        self.info_request = CBInfoRequest()

    @patch('cloud_builder.info_request.info_request.CBIdentity')
    def test_set_info_request(self, mock_CBIdentity):
        self.info_request.set_info_request('vim')
        assert self.info_request.get_data() == {
            'package': 'vim',
            'request_id': mock_CBIdentity.get_request_id.return_value,
            'schema_version': 0.1
        }
