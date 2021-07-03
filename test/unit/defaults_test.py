import io
from mock import (
    patch, MagicMock
)

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

    @patch('os.path.isfile')
    @patch('yaml.safe_load')
    def test_get_package_config(
        self, mock_yaml_safe_load, mock_os_path_isfile
    ):
        mock_os_path_isfile.return_value = True
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            Defaults.get_package_config('path/to/package')
            mock_open.assert_called_once_with(
                'path/to/package/cloud_builder.yml', 'r'
            )
            mock_yaml_safe_load.assert_called_once_with(file_handle)
            mock_open.reset_mock()
            mock_yaml_safe_load.reset_mock()
            Defaults.get_package_config('path/to/package', 'custom_file')
            mock_open.assert_called_once_with(
                'custom_file', 'r'
            )
            mock_yaml_safe_load.assert_called_once_with(file_handle)

    def test_get_kafka_config(self):
        with patch.dict('os.environ', {'HOME': 'users_home'}):
            assert Defaults.get_kafka_config() == \
                'users_home/.config/cb/kafka.yml'
