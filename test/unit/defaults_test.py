from mock import patch

from cloud_builder.defaults import Defaults


class TestDefaults:
    def test_get_runner_results_root(self):
        assert Defaults.get_runner_results_root() == 'home/abuild'

    def test_get_cb_logfile(self):
        assert Defaults.get_cb_logfile() == '/var/log/cloud_builder.log'

    def test_get_runner_package_root(self):
        assert Defaults.get_runner_package_root() == '/var/tmp/CB'

    def test_get_status_flags(self):
        flags = Defaults.get_status_flags()
        assert flags.package_rebuild == \
            'package rebuild requested'
        assert flags.package_rebuild_clean == \
            'package rebuild on new buildroot'
        assert flags.package_source_rebuild == \
            'package rebuild due to source change'
        assert flags.package_source_rebuild_clean == \
            'package rebuild on new buildroot due to source change'
        assert flags.package_build_failed == \
            'package build failed'
        assert flags.package_build_succeeded == \
            'package build succeeded'
        assert flags.package_build_running == \
            'package build running'
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

    def test_get_cloud_builder_metadata_file_name(self):
        assert Defaults.get_cloud_builder_metadata_file_name() == \
            'cloud_builder.yml'

    def test_get_cloud_builder_kiwi_file_name(self):
        assert Defaults.get_cloud_builder_kiwi_file_name() == \
            'cloud_builder.kiwi'

    def test_get_projects_path(self):
        with patch.dict('os.environ', {'HOME': 'root'}):
            assert Defaults.get_projects_path(
                '/root/cloud_builder_sources/'
                'projects/MS/python-kiwi_boxed_plugin'
            ) == 'projects/MS'

    def test_get_repo_root(self):
        assert Defaults.get_repo_root() == '/srv/www/projects'
