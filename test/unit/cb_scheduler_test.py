import sys
import io
import signal
from textwrap import dedent
from mock import (
    patch, Mock, MagicMock, call
)

from cloud_builder.cb_scheduler import (
    main,
    handle_build_requests,
    build_package,
    reset_build_if_running,
    check_package_sources,
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
    @patch('cloud_builder.cb_scheduler.Defaults')
    @patch('platform.machine')
    def test_handle_build_requests_platform_ok(
        self, mock_platform_machine, mock_Defaults, mock_CBMessageBroker,
        mock_CBCloudLogger, mock_build_package, mock_get_running_builds,
        mock_CBResponse
    ):
        log = Mock()
        mock_platform_machine.return_value = 'x86_64'
        request = {
            'action': 'package source changed',
            'arch': 'x86_64',
            'package': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.1
        }
        broker = Mock()
        broker.read.return_value = [Mock(value=request)]
        broker.validate_package_request.return_value = request
        mock_CBCloudLogger.return_value = log
        mock_CBMessageBroker.new.return_value = broker
        build_instances = [
            20, 8, 5
        ]

        def running_limit():
            return build_instances.pop()

        mock_get_running_builds.side_effect = running_limit

        handle_build_requests(5000, 10)

        log.response.assert_called_once_with(
            mock_CBResponse.return_value
        )

        broker.acknowledge.assert_called_once_with()
        mock_build_package.assert_called_once_with(request)
        broker.close.assert_called_once_with()

    @patch('cloud_builder.cb_scheduler.CBResponse')
    @patch('cloud_builder.cb_scheduler.get_running_builds')
    @patch('cloud_builder.cb_scheduler.build_package')
    @patch('cloud_builder.cb_scheduler.CBCloudLogger')
    @patch('cloud_builder.cb_scheduler.CBMessageBroker')
    @patch('cloud_builder.cb_scheduler.Defaults')
    @patch('platform.machine')
    def test_handle_build_requests_platform_mismatch(
        self, mock_platform_machine, mock_Defaults, mock_CBMessageBroker,
        mock_CBCloudLogger, mock_build_package, mock_get_running_builds,
        mock_CBResponse
    ):
        log = Mock()
        mock_platform_machine.return_value = 'aarch64'
        request = {
            'action': 'package source changed',
            'arch': 'x86_64',
            'package': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.1
        }
        broker = Mock()
        broker.read.return_value = [Mock(value=request)]
        broker.validate_package_request.return_value = request
        mock_CBCloudLogger.return_value = log
        mock_CBMessageBroker.new.return_value = broker
        build_instances = [
            20, 8, 5
        ]

        def running_limit():
            return build_instances.pop()

        mock_get_running_builds.side_effect = running_limit

        handle_build_requests(5000, 10)

        log.response.assert_called_once_with(
            mock_CBResponse.return_value
        )

        broker.close.assert_called_once_with()

    @patch('cloud_builder.cb_scheduler.CBMetaData')
    @patch('cloud_builder.cb_scheduler.CBCloudLogger')
    @patch('cloud_builder.cb_scheduler.Command.run')
    @patch('cloud_builder.cb_scheduler.Defaults')
    @patch('cloud_builder.cb_scheduler.check_package_sources')
    @patch('cloud_builder.cb_scheduler.create_run_script')
    @patch('cloud_builder.cb_scheduler.reset_build_if_running')
    def test_build_package(
        self, mock_reset_build_if_running, mock_create_run_script,
        mock_check_package_sources, mock_Defaults,
        mock_Command_run, mock_CBCloudLogger, mock_CBMetaData
    ):
        log = Mock()
        mock_CBCloudLogger.return_value = log
        mock_check_package_sources.return_value = True
        status_flags = Mock(package_changed='package source changed')
        mock_Defaults.get_status_flags.return_value = status_flags
        mock_Defaults.get_runner_project_dir.return_value = \
            'cloud_builder_sources'
        request = {
            'action': 'package source changed',
            'arch': 'x86_64',
            'package': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.1
        }
        build_package(request)
        mock_reset_build_if_running.assert_called_once_with(
            mock_CBMetaData.get_package_config.return_value,
            request, log
        )
        mock_create_run_script.assert_called_once_with(
            mock_CBMetaData.get_package_config.return_value,
            request, 'cloud_builder_sources/vim'
        )
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
            'package': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.1
        }
        package_config = {
            'name': 'vim',
            'distributions': [
                {'dist': 'TW', 'arch': 'x86_64'}
            ]
        }
        log = Mock()
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.return_value = '1234'
            reset_build_if_running(package_config, request, log)
            mock_open.assert_called_once_with('/var/tmp/CB/vim.pid')
            mock_os_kill.assert_called_once_with(
                1234, signal.SIGTERM
            )
            log.response.assert_called_once_with(
                mock_CBResponse.return_value
            )

    def test_get_running_builds(self):
        assert get_running_builds() == 0

    @patch('os.path.isdir')
    def test_check_package_sources(self, mock_os_path_isdir):
        request = {
            'action': 'package source changed',
            'arch': 'x86_64',
            'package': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.1
        }
        mock_os_path_isdir.return_value = False
        assert check_package_sources('path', request, Mock()) is False
        mock_os_path_isdir.return_value = True
        assert check_package_sources('path', request, Mock()) is True

    def test_create_run_script(self):
        request = {
            'action': 'package source changed',
            'arch': 'x86_64',
            'package': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.1
        }
        package_config = {
            'name': 'vim',
            'distributions': [
                {'dist': 'TW', 'arch': 'x86_64'}
            ]
        }
        script_code = dedent('''
            #!/bin/bash

            set -e

            function finish {
                kill $(jobs -p) &>/dev/null
            }

            {
            trap finish EXIT

            cb-prepare --root /var/tmp/CB \\
                --package source_path \\
                --profile TW.x86_64 \\
                --request-id c8becd30-a5f6-43a6-a4f4-598ec1115b17
            cb-run --root /var/tmp/CB/vim@TW.x86_64 &> /var/tmp/CB/vim@TW.x86_64.log \\
                --request-id c8becd30-a5f6-43a6-a4f4-598ec1115b17

            } &>/var/tmp/CB/vim.log &

            echo $! > /var/tmp/CB/vim.pid
        ''')
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            create_run_script(package_config, request, 'source_path')
            mock_open.assert_called_once_with(
                '/var/tmp/CB/vim.sh', 'w'
            )
            file_handle.write.assert_called_once_with(script_code)
