from mock import (
    patch, Mock
)

from cloud_builder.project_metadata.project_metadata import CBProjectMetaData


class TestCBProjectMetaData:
    def test_get_project_config_ok(self):
        metadata = CBProjectMetaData.get_project_config(
            'path/to/package', Mock(), 'request_id',
            '../data/cloud_builder-ok.yml'
        )
        assert metadata == {
            'schema_version': 0.1,
            'name': 'xclock',
            'distributions': [
                {'dist': 'TW', 'arch': 'x86_64', 'runner_group': 'suse'},
                {'dist': 'TW', 'arch': 'aarch64', 'runner_group': 'suse'}
            ]
        }

    @patch('cloud_builder.project_metadata.project_metadata.CBResponse')
    @patch('cloud_builder.broker.CBMessageBroker.new')
    def test_get_project_config_invalid(
        self, mock_CBMessageBroker, mock_CBResponse
    ):
        response = mock_CBResponse.return_value
        metadata = CBProjectMetaData.get_project_config(
            'path/to/package', Mock(), 'request_id',
            '../data/cloud_builder-invalid.yml'
        )
        assert metadata == {}
        assert response.set_project_invalid_metadata_response.called

    @patch('cloud_builder.project_metadata.project_metadata.CBResponse')
    @patch('cloud_builder.broker.CBMessageBroker.new')
    def test_get_package_config_broken(
        self, mock_CBMessageBroker, mock_CBResponse
    ):
        response = mock_CBResponse.return_value
        metadata = CBProjectMetaData.get_project_config(
            'path/to/package', Mock(), 'request_id',
            '../data/cloud_builder-broken.yml'
        )
        assert metadata == {}
        assert response.set_project_invalid_metadata_response.called
