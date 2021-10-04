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
    build_image,
    reset_build_if_running,
    is_request_valid,
    create_package_run_script,
    create_image_run_script,
    get_running_builds,
    request_validation_type,
    is_active
)


class TestCBScheduler:
    def setup(self):
        self.status_flags = Defaults.get_status_flags()
        sys.argv = [
            sys.argv[0]
        ]

    @patch('cloud_builder.cb_scheduler.get_running_builds')
    @patch('cloud_builder.cb_scheduler.handle_build_requests')
    @patch('cloud_builder.cb_scheduler.Privileges.check_for_root_permissions')
    @patch('cloud_builder.cb_scheduler.Path.create')
    @patch('cloud_builder.cb_scheduler.BlockingScheduler')
    @patch('cloud_builder.cb_scheduler.Defaults')
    @patch('cloud_builder.cb_scheduler.CBCloudLogger')
    def test_main_normal_runtime(
        self, mock_CBCloudLogger, mock_Defaults, mock_BlockingScheduler,
        mock_Path_create, mock_Privileges_check_for_root_permissions,
        mock_handle_build_requests, mock_get_running_builds
    ):
        project_scheduler = Mock()
        mock_BlockingScheduler.return_value = project_scheduler
        main()
        mock_Privileges_check_for_root_permissions.assert_called_once_with()
        mock_Path_create.assert_called_once_with(
            mock_Defaults.get_runner_root.return_value
        )
        mock_handle_build_requests.assert_called_once_with(
            5000, 10, mock_CBCloudLogger.return_value
        )
        mock_BlockingScheduler.assert_called_once_with()
        project_scheduler.start.assert_called_once_with()

    @patch('cloud_builder.cb_scheduler.Privileges.check_for_root_permissions')
    @patch('cloud_builder.cb_scheduler.Path.create')
    @patch('cloud_builder.cb_scheduler.Defaults')
    @patch('sys.exit')
    @patch('cloud_builder.cb_scheduler.CBCloudLogger')
    def test_main_poll_timeout_greater_than_update_interval(
        self, mock_CBCloudLogger, mock_sys_exit, mock_Defaults,
        mock_Path_create, mock_Privileges_check_for_root_permissions,
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
        handle_build_requests(5000, 10, log)
        log.info.assert_called_once_with(
            'Max running builds limit reached'
        )

    @patch('cloud_builder.cb_scheduler.CBResponse')
    @patch('cloud_builder.cb_scheduler.get_running_builds')
    @patch('cloud_builder.cb_scheduler.build_image')
    @patch('cloud_builder.cb_scheduler.CBCloudLogger')
    @patch('cloud_builder.cb_scheduler.CBMessageBroker')
    @patch('cloud_builder.cb_scheduler.is_request_valid')
    def test_handle_image_build_requests(
        self, mock_is_request_valid, mock_CBMessageBroker,
        mock_CBCloudLogger, mock_build_image, mock_get_running_builds,
        mock_CBResponse
    ):
        log = Mock()
        request = {
            'action': self.status_flags.image_source_rebuild,
            'image': {
                'arch': 'x86_64',
                'selection': 'standard'
            },
            'project': 'myimage',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        project_config = {
            'name': 'myimage',
            'images': [
                {
                    'selection': {
                        'name': 'standard'
                    }
                }
            ]
        }
        broker = Mock()
        broker.read.return_value = [Mock(value=request)]
        broker.validate_build_request.return_value = request
        mock_CBCloudLogger.return_value = log
        mock_CBMessageBroker.new.return_value = broker
        mock_is_request_valid.return_value = request_validation_type(
            project_config=project_config,
            response=Mock(),
            is_valid=True
        )
        build_instances = [
            20, 8, 5
        ]

        def running_limit():
            return build_instances.pop()

        mock_get_running_builds.side_effect = running_limit

        handle_build_requests(5000, 10, log)

        log.response.assert_called_once_with(
            mock_is_request_valid.return_value.response, broker
        )

        broker.acknowledge.assert_called_once_with()

        mock_build_image.assert_called_once_with(
            request, project_config, broker, log
        )

        broker.close.assert_called_once_with()

    @patch('cloud_builder.cb_scheduler.CBResponse')
    @patch('cloud_builder.cb_scheduler.get_running_builds')
    @patch('cloud_builder.cb_scheduler.build_package')
    @patch('cloud_builder.cb_scheduler.CBCloudLogger')
    @patch('cloud_builder.cb_scheduler.CBMessageBroker')
    @patch('cloud_builder.cb_scheduler.is_request_valid')
    def test_handle_package_build_requests(
        self, mock_is_request_valid, mock_CBMessageBroker,
        mock_CBCloudLogger, mock_build_package, mock_get_running_builds,
        mock_CBResponse
    ):
        log = Mock()
        request = {
            'action': self.status_flags.package_rebuild,
            'package': {
                'arch': 'x86_64',
                'dist': 'TW',
            },
            'project': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        package_config = {
            'name': 'vim', 'distributions': []
        }
        broker = Mock()
        broker.read.return_value = [Mock(value=request)]
        broker.validate_build_request.return_value = request
        mock_CBCloudLogger.return_value = log
        mock_CBMessageBroker.new.return_value = broker
        mock_is_request_valid.return_value = request_validation_type(
            project_config=package_config,
            response=Mock(),
            is_valid=True
        )
        build_instances = [
            20, 8, 5
        ]

        def running_limit():
            return build_instances.pop()

        mock_get_running_builds.side_effect = running_limit

        handle_build_requests(5000, 10, log)

        mock_build_package.assert_called_once_with(
            request, broker, log
        )

        broker.close.assert_called_once_with()

    @patch('cloud_builder.cb_scheduler.CBCloudLogger')
    @patch('cloud_builder.cb_scheduler.Command.run')
    @patch('cloud_builder.cb_scheduler.Defaults.get_runner_project_dir')
    @patch('cloud_builder.cb_scheduler.create_image_run_script')
    @patch('cloud_builder.cb_scheduler.reset_build_if_running')
    def test_build_image(
        self, mock_reset_build_if_running, mock_create_image_run_script,
        mock_Defaults_get_runner_project_dir, mock_Command_run,
        mock_CBCloudLogger
    ):
        log = Mock()
        broker = Mock()
        request = {
            'action': self.status_flags.image_source_rebuild,
            'image': {
                'arch': 'x86_64',
                'selection': 'standard'
            },
            'project': 'myimage',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        project_config = {
            'name': 'myimage',
            'images': [
                {
                    'selection': {
                        'name': 'standard'
                    }
                }
            ]
        }
        build_image(request, project_config, broker, log)
        mock_reset_build_if_running.assert_called_once_with(
            request, log, broker
        )
        mock_create_image_run_script.assert_called_once_with(
            request, project_config
        )
        assert mock_Command_run.call_args_list == [
            call(
                [
                    'git', '-C',
                    mock_Defaults_get_runner_project_dir.return_value,
                    'pull'
                ]
            ),
            call(
                ['bash', mock_create_image_run_script.return_value]
            )
        ]

    @patch('cloud_builder.cb_scheduler.CBCloudLogger')
    @patch('cloud_builder.cb_scheduler.Command.run')
    @patch('cloud_builder.cb_scheduler.Defaults.get_runner_project_dir')
    @patch('cloud_builder.cb_scheduler.create_package_run_script')
    @patch('cloud_builder.cb_scheduler.reset_build_if_running')
    def test_build_package(
        self, mock_reset_build_if_running, mock_create_package_run_script,
        mock_Defaults_get_runner_project_dir,
        mock_Command_run, mock_CBCloudLogger
    ):
        log = Mock()
        broker = Mock()
        mock_CBCloudLogger.return_value = log
        mock_Defaults_get_runner_project_dir.return_value = \
            'cloud_builder_sources'
        request = {
            'action': self.status_flags.package_rebuild_clean,
            'package': {
                'arch': 'x86_64',
                'dist': 'TW'
            },
            'project': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        build_package(request, broker, log)
        mock_reset_build_if_running.assert_called_once_with(
            request, log, broker
        )
        mock_create_package_run_script.assert_called_once_with(request, True)
        assert mock_Command_run.call_args_list == [
            call(
                [
                    'git', '-C',
                    mock_Defaults_get_runner_project_dir.return_value,
                    'pull'
                ]
            ),
            call(
                ['bash', mock_create_package_run_script.return_value]
            )
        ]

    @patch('os.path.isfile')
    @patch('psutil.pid_exists')
    @patch('os.kill')
    @patch('cloud_builder.cb_scheduler.CBResponse')
    def test_reset_build_if_running_for_package_build(
        self, mock_CBResponse, mock_os_kill,
        mock_psutil_pid_exists, mock_path_isfile
    ):
        mock_path_isfile.return_value = True
        mock_psutil_pid_exists.return_value = True
        request = {
            'action': self.status_flags.package_source_rebuild,
            'package': {
                'arch': 'x86_64',
                'dist': 'TW'
            },
            'project': 'projects/MS/vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        log = Mock()
        broker = Mock()
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.return_value = '1234'
            reset_build_if_running(request, log, broker)
            mock_open.assert_called_once_with(
                '/var/tmp/CB/projects/MS/vim@TW.x86_64.pid'
            )
            mock_os_kill.assert_called_once_with(
                1234, signal.SIGTERM
            )
            log.response.assert_called_once_with(
                mock_CBResponse.return_value, broker
            )

    @patch('os.path.isfile')
    @patch('psutil.pid_exists')
    @patch('os.kill')
    @patch('cloud_builder.cb_scheduler.CBResponse')
    def test_reset_build_if_running_for_image_build(
        self, mock_CBResponse, mock_os_kill,
        mock_psutil_pid_exists, mock_path_isfile
    ):
        mock_path_isfile.return_value = True
        mock_psutil_pid_exists.return_value = True
        request = {
            'action': self.status_flags.package_source_rebuild,
            'image': {
                'arch': 'x86_64',
                'selection': 'standard'
            },
            'project': 'projects/images/leap/test-image-disk',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        log = Mock()
        broker = Mock()
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.return_value = '1234'
            reset_build_if_running(request, log, broker)
            mock_open.assert_called_once_with(
                '/var/tmp/CB/projects/'
                'images/leap/test-image-disk@standard.x86_64.pid'
            )
            mock_os_kill.assert_called_once_with(
                1234, signal.SIGTERM
            )
            log.response.assert_called_once_with(
                mock_CBResponse.return_value, broker
            )

    @patch('os.walk')
    @patch('psutil.pid_exists')
    def test_get_running_builds(self, mock_psutil_pid_exists, mock_walk):
        mock_psutil_pid_exists.return_value = True
        mock_walk.return_value = [
            ('/top', ('bar', 'baz'), ('spam', 'package.pid'))
        ]
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.return_value = '1234'
            assert get_running_builds() == 1
            mock_open.assert_called_once_with('/top/package.pid')

        mock_psutil_pid_exists.side_effect = Exception

        with patch('builtins.open', create=True) as mock_open:
            assert get_running_builds() == 0

    @patch('os.path.isdir')
    @patch('cloud_builder.cb_scheduler.CBResponse')
    def test_is_request_valid_no_sources(
        self, mock_CBResponse, mock_os_path_isdir
    ):
        response = Mock()
        mock_CBResponse.return_value = response
        request = {
            'action': self.status_flags.package_source_rebuild,
            'package': {
                'arch': 'x86_64',
                'dist': 'TW'
            },
            'project': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        mock_os_path_isdir.return_value = False
        assert is_request_valid('path', request, Mock()).project_config == {}

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('cloud_builder.cb_scheduler.CBResponse')
    def test_is_request_valid_no_package_metadata(
        self, mock_CBResponse, mock_os_path_isfile, mock_os_path_isdir
    ):
        response = Mock()
        mock_CBResponse.return_value = response
        request = {
            'action': self.status_flags.package_source_rebuild,
            'package': {
                'arch': 'x86_64',
                'dist': 'TW'
            },
            'project': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        mock_os_path_isdir.return_value = True
        mock_os_path_isfile.return_value = False
        assert is_request_valid('path', request, Mock()).project_config == {}

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('cloud_builder.cb_scheduler.CBResponse')
    @patch('cloud_builder.cb_scheduler.CBProjectMetaData')
    def test_is_request_valid_get_project_config_failed(
        self, mock_CBProjectMetaData, mock_CBResponse,
        mock_os_path_isfile, mock_os_path_isdir
    ):
        package_config = {}
        mock_CBProjectMetaData.get_project_config.return_value = package_config
        response = Mock()
        mock_CBResponse.return_value = response
        request = {
            'action': self.status_flags.package_source_rebuild,
            'package': {
                'arch': 'x86_64',
                'dist': 'TW'
            },
            'project': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        mock_os_path_isdir.return_value = True
        mock_os_path_isfile.return_value = True
        assert is_request_valid('path', request, Mock()).project_config == {}

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('cloud_builder.cb_scheduler.CBResponse')
    @patch('cloud_builder.cb_scheduler.CBProjectMetaData')
    def test_is_request_valid_incorrect_image_target(
        self, mock_CBProjectMetaData, mock_CBResponse,
        mock_os_path_isfile, mock_os_path_isdir
    ):
        package_config = {
            'name': 'myimage',
            'images': [
                {
                    'arch': 'x86_64',
                    'runner_group': 'FOO',
                    'selection': {
                        'name': 'standard'
                    }
                }
            ]
        }
        mock_CBProjectMetaData.get_project_config.return_value = package_config
        response = Mock()
        mock_CBResponse.return_value = response
        request = {
            'action': self.status_flags.image_source_rebuild,
            'image': {
                'arch': 'x86_64',
                'selection': 'standard'
            },
            'runner_group': 'suse',
            'project': 'myimage',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        mock_os_path_isdir.return_value = True
        mock_os_path_isfile.return_value = True
        assert is_request_valid('path', request, Mock()).project_config == {}

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('cloud_builder.cb_scheduler.CBResponse')
    @patch('cloud_builder.cb_scheduler.CBProjectMetaData')
    def test_is_request_valid_incorrect_package_target(
        self, mock_CBProjectMetaData, mock_CBResponse,
        mock_os_path_isfile, mock_os_path_isdir
    ):
        package_config = {
            'name': 'vim',
            'distributions': [
                {'dist': 'FOO', 'arch': 'x86_64', 'runner_group': 'suse'}
            ]
        }
        mock_CBProjectMetaData.get_project_config.return_value = package_config
        response = Mock()
        mock_CBResponse.return_value = response
        request = {
            'action': self.status_flags.package_source_rebuild,
            'package': {
                'arch': 'x86_64',
                'dist': 'TW'
            },
            'runner_group': 'suse',
            'project': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        mock_os_path_isdir.return_value = True
        mock_os_path_isfile.return_value = True
        assert is_request_valid('path', request, Mock()).project_config == {}

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('cloud_builder.cb_scheduler.CBResponse')
    @patch('cloud_builder.cb_scheduler.CBProjectMetaData')
    @patch('platform.machine')
    def test_is_request_valid_incompatible_host_arch(
        self, mock_platform_machine, mock_CBProjectMetaData, mock_CBResponse,
        mock_os_path_isfile, mock_os_path_isdir
    ):
        mock_platform_machine.return_value = 'aarch64'
        package_config = {
            'name': 'vim',
            'distributions': [
                {'dist': 'TW', 'arch': 'x86_64', 'runner_group': 'suse'}
            ]
        }
        mock_CBProjectMetaData.get_project_config.return_value = package_config
        response = Mock()
        mock_CBResponse.return_value = response
        request = {
            'action': self.status_flags.package_source_rebuild,
            'package': {
                'arch': 'x86_64',
                'dist': 'TW'
            },
            'runner_group': 'suse',
            'project': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        mock_os_path_isdir.return_value = True
        mock_os_path_isfile.return_value = True
        assert is_request_valid('path', request, Mock()).project_config == {}

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('cloud_builder.cb_scheduler.CBResponse')
    @patch('cloud_builder.cb_scheduler.CBProjectMetaData')
    @patch('platform.machine')
    def test_is_request_valid_for_image_build_all_good(
        self, mock_platform_machine, mock_CBProjectMetaData, mock_CBResponse,
        mock_os_path_isfile, mock_os_path_isdir
    ):
        mock_platform_machine.return_value = 'x86_64'
        package_config = {
            'name': 'myimage',
            'images': [
                {
                    'arch': 'x86_64',
                    'runner_group': 'suse',
                    'selection': {
                        'name': 'standard'
                    }
                }
            ]
        }
        mock_CBProjectMetaData.get_project_config.return_value = package_config
        response = Mock()
        mock_CBResponse.return_value = response
        request = {
            'action': self.status_flags.image_source_rebuild,
            'image': {
                'arch': 'x86_64',
                'selection': 'standard'
            },
            'runner_group': 'suse',
            'project': 'myimage',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        mock_os_path_isdir.return_value = True
        mock_os_path_isfile.return_value = True
        assert is_request_valid(
            'path', request, Mock()
        ).project_config == package_config

    @patch('os.path.isdir')
    @patch('os.path.isfile')
    @patch('cloud_builder.cb_scheduler.CBResponse')
    @patch('cloud_builder.cb_scheduler.CBProjectMetaData')
    @patch('platform.machine')
    def test_is_request_valid_for_package_build_all_good(
        self, mock_platform_machine, mock_CBProjectMetaData, mock_CBResponse,
        mock_os_path_isfile, mock_os_path_isdir
    ):
        mock_platform_machine.return_value = 'x86_64'
        package_config = {
            'name': 'vim',
            'distributions': [
                {'dist': 'TW', 'arch': 'x86_64', 'runner_group': 'suse'}
            ]
        }
        mock_CBProjectMetaData.get_project_config.return_value = package_config
        response = Mock()
        mock_CBResponse.return_value = response
        request = {
            'action': self.status_flags.package_source_rebuild,
            'package': {
                'arch': 'x86_64',
                'dist': 'TW'
            },
            'runner_group': 'suse',
            'project': 'vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        mock_os_path_isdir.return_value = True
        mock_os_path_isfile.return_value = True
        assert is_request_valid(
            'path', request, Mock()
        ).project_config == package_config

    @patch('cloud_builder.cb_scheduler.Path.create')
    def test_create_image_run_script_for_local_build(self, mock_Path_create):
        request = {
            'action': self.status_flags.image_local,
            'image': {
                'arch': 'x86_64',
                'selection': 'standard'
            },
            'project': 'projects/MS/myimage',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        project_config = {
            'name': 'myimage',
            'images': [
                {
                    'selection': {
                        'name': 'standard',
                        'profiles': ['profile'],
                        'build_arguments': ['--opt', 'a']
                    }
                }
            ]
        }
        script_code = dedent('''
            #!/bin/bash
            set -e
            rm -rf projects/MS/myimage@standard.x86_64
            cb-image \\
                --request-id c8becd30-a5f6-43a6-a4f4-598ec1115b17 \\
                --bundle-id 0 \\
                --description projects/MS/myimage \\
                --target-dir projects/MS/myimage@standard.x86_64 \\
                --local \\
                --profile profile -- --opt a
        ''')
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            create_image_run_script(
                request, project_config, local_build=True
            )
            mock_Path_create.assert_called_once_with('projects/MS')
            mock_open.assert_called_once_with(
                'projects/MS/myimage@standard.x86_64.sh', 'w'
            )
            file_handle.write.assert_called_once_with(script_code)

    @patch('cloud_builder.cb_scheduler.Defaults')
    @patch('cloud_builder.cb_scheduler.Path.create')
    def test_create_image_run_script_for_runner_build(
        self, mock_Path_create, mock_Defaults
    ):
        mock_Defaults.get_runner_project_dir.return_value = \
            'cloud_builder_sources'
        mock_Defaults.get_runner_root.return_value = \
            Defaults.get_runner_root()
        request = {
            'action': self.status_flags.image_local,
            'image': {
                'arch': 'x86_64',
                'selection': 'standard'
            },
            'project': 'projects/MS/myimage',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        project_config = {
            'name': 'myimage',
            'images': [
                {
                    'selection': {
                        'name': 'standard'
                    }
                }
            ]
        }
        script_code = dedent('''
            #!/bin/bash
            set -e

            rm -rf /var/tmp/CB/projects/MS/myimage@standard.x86_64

            function finish {{
                kill $(jobs -p) &>/dev/null
            }}

            {{
                trap finish EXIT
                cb-image \\
                    --request-id c8becd30-a5f6-43a6-a4f4-598ec1115b17 \\
                    --bundle-id 0 \\
                    --description cloud_builder_sources/projects/MS/myimage \\
                    --target-dir /var/tmp/CB/projects/MS/myimage@standard.x86_64 \\
                    {0} {1}
            }} &>>/var/tmp/CB/projects/MS/myimage@standard.x86_64.run.log &

            echo $! > /var/tmp/CB/projects/MS/myimage@standard.x86_64.pid
        ''').format('', '')
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            create_image_run_script(request, project_config)
            mock_Path_create.assert_called_once_with('/var/tmp/CB/projects/MS')
            mock_open.assert_called_once_with(
                '/var/tmp/CB/projects/MS/myimage@standard.x86_64.sh', 'w'
            )
            file_handle.write.assert_called_once_with(script_code)

    @patch('cloud_builder.cb_scheduler.Path.create')
    def test_create_package_run_script_for_local_build(self, mock_Path_create):
        request = {
            'action': self.status_flags.package_local,
            'package': {
                'arch': 'x86_64',
                'dist': 'TW'
            },
            'project': 'projects/MS/vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        script_code = dedent('''
            #!/bin/bash

            set -e

            if true; then
                rm -rf projects/MS/vim@TW.x86_64
            fi

            cb-prepare --root projects/MS/vim@TW.x86_64 \\
                --package projects/MS/vim \\
                --profile TW.x86_64 \\
                --request-id c8becd30-a5f6-43a6-a4f4-598ec1115b17 \\
                --local
            cb-run --root projects/MS/vim@TW.x86_64 \\
                --request-id c8becd30-a5f6-43a6-a4f4-598ec1115b17 \\
                --local
        ''')
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            create_package_run_script(request, True, True)
            mock_Path_create.assert_called_once_with('projects/MS')
            mock_open.assert_called_once_with(
                'projects/MS/vim@TW.x86_64.sh', 'w'
            )
            file_handle.write.assert_called_once_with(script_code)

    @patch('cloud_builder.cb_scheduler.Defaults')
    @patch('cloud_builder.cb_scheduler.Path.create')
    def test_create_package_run_script_for_runner_build(
        self, mock_Path_create, mock_Defaults
    ):
        mock_Defaults.get_runner_project_dir.return_value = \
            'cloud_builder_sources'
        mock_Defaults.get_runner_root.return_value = \
            Defaults.get_runner_root()
        request = {
            'action': self.status_flags.package_source_rebuild_clean,
            'package': {
                'arch': 'x86_64',
                'dist': 'TW'
            },
            'project': 'projects/MS/vim',
            'request_id': 'c8becd30-a5f6-43a6-a4f4-598ec1115b17',
            'schema_version': 0.2
        }
        script_code = dedent('''
            #!/bin/bash

            set -e

            rm -f /var/tmp/CB/projects/MS/vim@TW.x86_64.log

            if true; then
                rm -rf /var/tmp/CB/projects/MS/vim@TW.x86_64
            fi

            function finish {
                kill $(jobs -p) &>/dev/null
            }

            {
                trap finish EXIT
                cb-prepare --root /var/tmp/CB/projects/MS/vim@TW.x86_64 \\
                    --package cloud_builder_sources/projects/MS/vim \\
                    --profile TW.x86_64 \\
                    --request-id c8becd30-a5f6-43a6-a4f4-598ec1115b17
                cb-run --root /var/tmp/CB/projects/MS/vim@TW.x86_64 &> /var/tmp/CB/projects/MS/vim@TW.x86_64.build.log \\
                    --request-id c8becd30-a5f6-43a6-a4f4-598ec1115b17
            } &>>/var/tmp/CB/projects/MS/vim@TW.x86_64.run.log &

            echo $! > /var/tmp/CB/projects/MS/vim@TW.x86_64.pid
        ''')
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            create_package_run_script(request, True)
            mock_Path_create.assert_called_once_with('/var/tmp/CB/projects/MS')
            mock_open.assert_called_once_with(
                '/var/tmp/CB/projects/MS/vim@TW.x86_64.sh', 'w'
            )
            file_handle.write.assert_called_once_with(script_code)

    @patch('os.path.isfile')
    @patch('psutil.pid_exists')
    def test_is_active(self, mock_psutil_pid_exists, mock_os_path_is_file):
        mock_os_path_is_file.return_value = False
        assert is_active('/some/file.pid', Mock()) == 0
        mock_os_path_is_file.return_value = True
        mock_psutil_pid_exists.return_value = False
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.return_value = '1234'
            assert is_active('/some/file.pid', Mock()) == 0
