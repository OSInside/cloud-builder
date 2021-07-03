import re
from mock import (
    patch, Mock
)
from cloud_builder.identity import CBIdentity
from requests.exceptions import HTTPError


class TestCBIdentity:
    @patch('cloud_builder.identity.CBIdentity.get_external_ip')
    @patch('os.getpid')
    def test_get_id(self, mock_os_getpid, mock_get_external_ip):
        mock_os_getpid.return_value = 'pid'
        mock_get_external_ip.return_value = 'ip'
        assert CBIdentity.get_id('service', 'name') == \
            'service:ip:pid:name'

    def test_get_request_id(self):
        assert re.match(
            r'[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}',
            CBIdentity.get_request_id()
        ) is not None

    @patch('requests.get')
    def test_get_external_ip(self, mock_requests_get):
        mock_requests_get.return_value = Mock(content=b'IP')
        assert CBIdentity.get_external_ip() == 'IP'
        mock_requests_get.assert_called_once_with(
            'https://api.ipify.org'
        )

    @patch('requests.get')
    def test_get_external_ip_not_obtainable(self, mock_requests_get):
        mock_requests_get.side_effect = HTTPError
        assert CBIdentity.get_external_ip() == 'unknown'
