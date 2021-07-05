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
        assert flags.package_changed == 'package source changed'
        assert flags.package_build_failed == 'package build failed'
        assert flags.package_build_succeeded == 'package build succeeded'
        assert flags.buildroot_setup_failed == 'build root setup failed'
        assert flags.buildroot_setup_succeeded == 'build root setup succeeded'

    def test_get_runner_project_dir(self):
        with patch.dict('os.environ', {'HOME': 'users_home'}):
            assert Defaults.get_runner_project_dir() == \
                'users_home/cloud_builder_sources'

    def test_get_kafka_config(self):
        with patch.dict('os.environ', {'HOME': 'users_home'}):
            assert Defaults.get_kafka_config() == \
                'users_home/.config/cb/kafka.yml'
