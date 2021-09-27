import re
from mock import patch
from cloud_builder.identity import CBIdentity


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

    @patch('cloud_builder.identity.Defaults.get_broker_config')
    def test_get_external_ip(self, mock_get_broker_config):
        mock_get_broker_config.return_value = \
            '../data/etc/cloud_builder_broker.yml'
        assert CBIdentity.get_external_ip() == '10.10.0.1'

    @patch('cloud_builder.identity.Defaults.get_broker_config')
    def test_get_external_ip_not_obtainable(self, mock_get_broker_config):
        mock_get_broker_config.side_effect = Exception
        assert CBIdentity.get_external_ip() == 'unknown'
