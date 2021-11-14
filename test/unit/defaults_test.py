from mock import patch

from cloud_builder.defaults import Defaults


class TestDefaults:
    def test_get_runner_result_paths(self):
        assert Defaults.get_runner_result_paths() == [
            'home/abuild', 'usr/src/packages/DEBS'
        ]

    def test_get_cb_logfile(self):
        assert Defaults.get_cb_logfile() == '/var/log/cloud_builder.log'

    def test_get_runner_root(self):
        assert Defaults.get_runner_root() == '/var/tmp/CB'

    def test_get_status_flags(self):
        flags = Defaults.get_status_flags()
        assert flags.package_rebuild == \
            'package rebuild requested'
        assert flags.package_source_rebuild == \
            'package rebuild due to source change'
        assert flags.package_build_failed == \
            'package build failed'
        assert flags.package_build_succeeded == \
            'package build succeeded'
        assert flags.buildroot_setup_failed == \
            'build root setup failed'
        assert flags.buildroot_setup_succeeded == \
            'build root setup succeeded'
        assert flags.package_request_accepted == \
            'package request accepted'
        assert flags.incompatible_build_arch == \
            'incompatible build arch'
        assert flags.reset_running_build == \
            'reset running build'
        assert flags.project_not_existing == \
            'project does not exist'
        assert flags.project_metadata_not_existing == \
            'project metadata does not exist'
        assert flags.invalid_metadata == \
            'invalid package metadata'
        assert flags.package_target_not_configured == \
            'package target not configured'
        assert flags.image_target_not_configured == \
            'image target not configured'
        assert flags.image_source_rebuild == \
            'image rebuild due to source change'
        assert flags.image_request_accepted == \
            'image request accepted'

    def test_get_runner_project_dir(self):
        with patch.dict('os.environ', {'HOME': 'users_home'}):
            assert Defaults.get_runner_project_dir() == \
                'users_home/cloud_builder_sources'

    def test_get_broker_config(self):
        assert Defaults.get_broker_config() == '/etc/cloud_builder_broker.yml'

    def test_get_cb_ctl_config(self):
        with patch.dict('os.environ', {'HOME': 'users_home'}):
            assert Defaults.get_cb_ctl_config() == \
                'users_home/.config/cb/cbctl.yml'

    def test_get_build_request_queue_name(self):
        assert Defaults.get_build_request_queue_name() == 'cb-build-request'

    def test_get_response_queue_name(self):
        assert Defaults.get_response_queue_name() == 'cb-response'

    def test_get_info_request_queue_name(self):
        assert Defaults.get_info_request_queue_name() == 'cb-info-request'

    def test_get_info_response_queue_name(self):
        assert Defaults.get_info_response_queue_name() == 'cb-info-response'

    def test_get_cloud_builder_meta_project_setup_file_name(self):
        assert Defaults.get_cloud_builder_meta_project_setup_file_name() == \
            'cloud_builder.yml'

    def test_get_cloud_builder_meta_build_root_file_name(self):
        assert Defaults.get_cloud_builder_meta_build_root_file_name() == \
            'build_root.kiwi'

    def test_get_projects_path(self):
        with patch.dict('os.environ', {'HOME': 'root'}):
            assert Defaults.get_projects_path(
                '/root/cloud_builder_sources/'
                'projects/MS/python-kiwi_boxed_plugin'
            ) == 'projects/MS'

    def test_get_repo_root(self):
        assert Defaults.get_repo_root() == '/srv/www/projects'

    @patch('kiwi.defaults.Path.which')
    def test_get_kiwi(self, mock_Path_which):
        mock_Path_which.return_value = None
        assert Defaults.get_kiwi() == 'kiwi-ng'

        mock_Path_which.reset_mock()
        mock_Path_which.return_value = '/path/to/kiwi-ng'
        assert Defaults.get_kiwi() == mock_Path_which.return_value
        mock_Path_which.assert_called_once_with(
            'kiwi-ng', alternative_lookup_paths=['/usr/local/bin']
        )
