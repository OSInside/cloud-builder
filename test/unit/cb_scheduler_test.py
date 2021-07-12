import sys
import io
import signal
from textwrap import dedent
from mock import (
    patch, Mock, MagicMock, call
)

from cloud_builder.defaults import Defaults
from cloud_builder.cb_scheduler import (
    main,
    handle_build_requests,
    build_package,
    reset_build_if_running,
    is_request_valid,
    create_run_script,
    get_running_builds
)


class TestCBScheduler:
    def setup(self):
        sys.argv = [
            sys.argv[0]
        ]

    @patch('cloud_builder.cb_scheduler.get_running_builds')
    @patch('cloud_builder.cb_scheduler.handle_build_requests')
    @patch('cloud_builder.cb_scheduler.Privileges.check_for_root_permissions')
    @patch('cloud_builder.cb_scheduler.Path.create')
    @patch('cloud_builder.cb_scheduler.BlockingScheduler')
    @patch('cloud_builder.cb_scheduler.Defaults')
    def test_main_normal_runtime(
        self, mock_Defaults, mock_BlockingScheduler, mock_Path_create,
        mock_Privileges_check_for_root_permissions,
        mock_handle_build_requests, mock_get_running_builds
    ):
        project_scheduler = Mock()
        mock_BlockingScheduler.return_value = project_scheduler
        main()
        mock_Privileges_check_for_root_permissions.assert_called_once_with()
        mock_Path_create.assert_called_once_with(
            mock_Defaults.get_runner_package_root.return_value
        )
        mock_handle_build_requests.assert_called_once_with(
            5000, 10
        )
        mock_BlockingScheduler.assert_called_once_with()
        project_scheduler.start.assert_called_once_with()

    @patch('cloud_builder.cb_scheduler.Privileges.check_for_root_permissions')
    @patch('cloud_builder.cb_scheduler.Path.create')
    @patch('cloud_builder.cb_scheduler.Defaults')
    @patch('sys.exit')
    def test_main_poll_timeout_greater_than_update_interval(
        self, mock_sys_exit, mock_Defaults, mock_Path_create,
        mock_Privileges_check_for_root_permissions,
    ):
        sys.argv = [
            sys.argv[0], '--poll-timeout', '20000', '--update-interval', '10'
        ]
        main()
        mock_sys_exit.assert_called_once_with(1)

    @patch('cloud_builder.cb_scheduler.get_running_builds')
    @patch('cloud_builder.cb_scheduler.CBCloudLogger')
    def test_handle_build_requests_runner_busy(
        self, mock_CBCloudLogger, mock_get_running_builds
    ):
        log = Mock()
        mock_CBCloudLogger.return_value = log
        mock_get_running_builds.return_value = 20
        handle_build_requests(5000, 10)
        log.info.assert_called_once_with(
            'Max running builds limit reached'
        )

    @patch('cloud_builder.cb_scheduler.CBResponse')
    @patch('cloud_builder.cb_scheduler.get_running_builds')
    @patch('cloud_builder.cb_scheduler.build_package')
    @patch('cloud_builder.cb_scheduler.CBCloudLogger')
    @patch('cloud_builder.cb_scheduler.CBMessageBroker')
    @patch('cloud_builder.cb_scheduler.is_request_valid')
    def test_handle_build_requests(
        self, mock_is_request_valid, mock_CBMessageBroker,
        mock_CBCloudLogger, mock_build_package, mock_get_running_builds,
        mock_CBResponse
    ):
        log = Mock()
        request = {
            'action': 'package source changed',
            'arch': 'x86_64',
            'dist': 'TW',
            'package': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.1
        }
        package_config = {
            'name': 'vim', 'distributions': []
        }
        broker = Mock()
        broker.read.return_value = [Mock(value=request)]
        broker.validate_package_request.return_value = request
        mock_CBCloudLogger.return_value = log
        mock_CBMessageBroker.new.return_value = broker
        mock_is_request_valid.return_value = package_config
        build_instances = [
            20, 8, 5
        ]

        def running_limit():
            return build_instances.pop()

        mock_get_running_builds.side_effect = running_limit

        handle_build_requests(5000, 10)

        mock_build_package.assert_called_once_with(
            request, broker, package_config
        )

        broker.close.assert_called_once_with()

    @patch('cloud_builder.cb_scheduler.CBCloudLogger')
    @patch('cloud_builder.cb_scheduler.Command.run')
    @patch('cloud_builder.cb_scheduler.Defaults')
    @patch('cloud_builder.cb_scheduler.create_run_script')
    @patch('cloud_builder.cb_scheduler.reset_build_if_running')
    def test_build_package(
        self, mock_reset_build_if_running, mock_create_run_script,
        mock_Defaults, mock_Command_run, mock_CBCloudLogger
    ):
        log = Mock()
        broker = Mock()
        mock_CBCloudLogger.return_value = log
        status_flags = Mock(package_changed='package source changed')
        mock_Defaults.get_status_flags.return_value = status_flags
        mock_Defaults.get_runner_project_dir.return_value = \
            'cloud_builder_sources'
        request = {
            'action': 'package source changed',
            'arch': 'x86_64',
            'dist': 'TW',
            'package': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.1
        }
        package_config = {
            'name': 'vim', 'distributions': []
        }
        build_package(request, broker, package_config)
        mock_reset_build_if_running.assert_called_once_with(
            request, log, broker
        )
        mock_create_run_script.assert_called_once_with(request)
        assert mock_Command_run.call_args_list == [
            call(
                [
                    'git', '-C',
                    mock_Defaults.get_runner_project_dir.return_value,
                    'pull'
                ]
            ),
            call(
                ['bash', mock_create_run_script.return_value]
            )
        ]

    @patch('os.path.isfile')
    @patch('psutil.pid_exists')
    @patch('os.kill')
    @patch('cloud_builder.cb_scheduler.CBResponse')
    def test_reset_build_if_running(
        self, mock_CBResponse, mock_os_kill,
        mock_psutil_pid_exists, mock_path_isfile
    ):
        mock_path_isfile.return_value = True
        mock_psutil_pid_exists.return_value = True
        request = {
            'action': 'package source changed',
            'arch': 'x86_64',
            'dist': 'TW',
            'package': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.1
        }
        log = Mock()
        broker = Mock()
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.return_value = '1234'
            reset_build_if_running(request, log, broker)
            mock_open.assert_called_once_with('/var/tmp/CB/vim@TW.x86_64.pid')
            mock_os_kill.assert_called_once_with(
                1234, signal.SIGTERM
            )
            log.response.assert_called_once_with(
                mock_CBResponse.return_value, broker
            )

    def test_get_running_builds(self):
        assert get_running_builds() == 0

    @patch('os.path.isdir')
    @patch('cloud_builder.cb_scheduler.CBResponse')
    def test_is_request_valid_no_sources(
        self, mock_CBResponse, mock_os_path_isdir
    ):
        response = Mock()
        mock_CBResponse.return_value = response
        request = {
            'action': 'package source changed',
            'arch': 'x86_64',
            'dist': 'TW',
            'package': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.1
        }
        log = Mock()
        broker = Mock()
        mock_os_path_isdir.return_value = False
        assert is_request_valid('path', request, log, broker) == {}
        log.response.assert_called_once_with(response, broker)

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('cloud_builder.cb_scheduler.CBResponse')
    def test_is_request_valid_no_package_metadata(
        self, mock_CBResponse, mock_os_path_isfile, mock_os_path_isdir
    ):
        response = Mock()
        mock_CBResponse.return_value = response
        request = {
            'action': 'package source changed',
            'arch': 'x86_64',
            'dist': 'TW',
            'package': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.1
        }
        log = Mock()
        broker = Mock()
        mock_os_path_isdir.return_value = True
        mock_os_path_isfile.return_value = False
        assert is_request_valid('path', request, log, broker) == {}
        log.response.assert_called_once_with(response, broker)

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('cloud_builder.cb_scheduler.CBResponse')
    @patch('cloud_builder.cb_scheduler.CBPackageMetaData')
    def test_is_request_valid_incorrect_target(
        self, mock_CBPackageMetaData, mock_CBResponse,
        mock_os_path_isfile, mock_os_path_isdir
    ):
        package_config = {
            'name': 'vim',
            'distributions': [
                {'dist': 'FOO', 'arch': 'x86_64'}
            ]
        }
        mock_CBPackageMetaData.get_package_config.return_value = package_config
        response = Mock()
        mock_CBResponse.return_value = response
        request = {
            'action': 'package source changed',
            'arch': 'x86_64',
            'dist': 'TW',
            'package': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.1
        }
        log = Mock()
        broker = Mock()
        mock_os_path_isdir.return_value = True
        mock_os_path_isfile.return_value = True
        assert is_request_valid('path', request, log, broker) == {}
        log.response.assert_called_once_with(response, broker)

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('cloud_builder.cb_scheduler.CBResponse')
    @patch('cloud_builder.cb_scheduler.CBPackageMetaData')
    @patch('platform.machine')
    def test_is_request_valid_incompatible_host_arch(
        self, mock_platform_machine, mock_CBPackageMetaData, mock_CBResponse,
        mock_os_path_isfile, mock_os_path_isdir
    ):
        mock_platform_machine.return_value = 'aarch64'
        package_config = {
            'name': 'vim',
            'distributions': [
                {'dist': 'TW', 'arch': 'x86_64'}
            ]
        }
        mock_CBPackageMetaData.get_package_config.return_value = package_config
        response = Mock()
        mock_CBResponse.return_value = response
        request = {
            'action': 'package source changed',
            'arch': 'x86_64',
            'dist': 'TW',
            'package': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.1
        }
        log = Mock()
        broker = Mock()
        mock_os_path_isdir.return_value = True
        mock_os_path_isfile.return_value = True
        assert is_request_valid('path', request, log, broker) == {}
        log.response.assert_called_once_with(response, broker)

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('cloud_builder.cb_scheduler.CBResponse')
    @patch('cloud_builder.cb_scheduler.CBPackageMetaData')
    @patch('platform.machine')
    def test_is_request_valid_all_good(
        self, mock_platform_machine, mock_CBPackageMetaData, mock_CBResponse,
        mock_os_path_isfile, mock_os_path_isdir
    ):
        mock_platform_machine.return_value = 'x86_64'
        package_config = {
            'name': 'vim',
            'distributions': [
                {'dist': 'TW', 'arch': 'x86_64'}
            ]
        }
        mock_CBPackageMetaData.get_package_config.return_value = package_config
        response = Mock()
        mock_CBResponse.return_value = response
        request = {
            'action': 'package source changed',
            'arch': 'x86_64',
            'dist': 'TW',
            'package': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.1
        }
        log = Mock()
        broker = Mock()
        mock_os_path_isdir.return_value = True
        mock_os_path_isfile.return_value = True
        assert is_request_valid('path', request, log, broker) == package_config
        log.response.assert_called_once_with(response, broker)
        broker.acknowledge.assert_called_once_with()

    @patch('cloud_builder.cb_scheduler.Defaults')
    def test_create_run_script(self, mock_Defaults):
        mock_Defaults.get_runner_project_dir.return_value = \
            'cloud_builder_sources'
        mock_Defaults.get_runner_package_root.return_value = \
            Defaults.get_runner_package_root()
        request = {
            'action': 'package source changed',
            'arch': 'x86_64',
            'dist': 'TW',
            'package': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.1
        }
        script_code = dedent('''
            #!/bin/bash

            set -e

            rm -f /var/tmp/CB/vim@TW.x86_64.log

            function finish {
                kill $(jobs -p) &>/dev/null
            }

            {
                trap finish EXIT
                cb-prepare --root /var/tmp/CB \\
                    --package cloud_builder_sources/vim \\
                    --profile TW.x86_64 \\
                    --request-id c8becd30-a5f6-43a6-a4f4-598ec1115b17
                cb-run --root /var/tmp/CB/vim@TW.x86_64 &> /var/tmp/CB/vim@TW.x86_64.build.log \\
                    --request-id c8becd30-a5f6-43a6-a4f4-598ec1115b17
            } &>>/var/tmp/CB/vim@TW.x86_64.run.log &

            echo $! > /var/tmp/CB/vim@TW.x86_64.pid
        ''')
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            create_run_script(request)
            mock_open.assert_called_once_with(
                '/var/tmp/CB/vim@TW.x86_64.sh', 'w'
            )
            file_handle.write.assert_called_once_with(script_code)
