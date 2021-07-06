from mock import (
    patch, Mock
)

from cloud_builder.metadata import CBMetaData


class TestCBMetaData:
    def test_get_package_config_ok(self):
        metadata = CBMetaData.get_package_config(
            'path/to/package', Mock(), 'request_id',
            '../data/cloud_builder-ok.yml'
        )
        assert metadata == {
            'schema_version': 0.1,
            'name': 'xclock',
            'distributions': [
                {'dist': 'TW', 'arch': 'x86_64'},
                {'dist': 'TW', 'arch': 'aarch64'}
            ]
        }

    @patch('cloud_builder.metadata.CBResponse')
    def test_get_package_config_invalid(self, mock_CBResponse):
        response = mock_CBResponse.return_value
        metadata = CBMetaData.get_package_config(
            'path/to/package', Mock(), 'request_id',
            '../data/cloud_builder-invalid.yml'
        )
        assert metadata == {}
        assert response.set_package_invalid_metadata_response.called

    @patch('cloud_builder.metadata.CBResponse')
    def test_get_package_config_broken(self, mock_CBResponse):
        response = mock_CBResponse.return_value
        metadata = CBMetaData.get_package_config(
            'path/to/package', Mock(), 'request_id',
            '../data/cloud_builder-broken.yml'
        )
        assert metadata == {}
        assert response.set_package_invalid_metadata_response.called
