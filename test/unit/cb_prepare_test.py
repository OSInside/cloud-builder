import sys
import io
from textwrap import dedent
from mock import (
    patch, Mock, MagicMock, call
)

from cloud_builder.cb_prepare import main


class TestCBPrepare:
    def setup(self):
        sys.argv = [
            sys.argv[0]
        ]

    @patch('cloud_builder.cb_prepare.Privileges.check_for_root_permissions')
    @patch('cloud_builder.cb_prepare.Command.run')
    @patch('cloud_builder.cb_prepare.CBResponse')
    @patch('cloud_builder.cb_prepare.CBCloudLogger')
    @patch('cloud_builder.cb_prepare.CBMessageBroker')
    @patch('cloud_builder.cb_prepare.Path')
    @patch('cloud_builder.cb_prepare.DataSync')
    @patch('os.system')
    @patch('sys.exit')
    def test_main_normal_runtime(
        self, mock_sys_exit, mock_os_system, mock_DataSync,
        mock_Path, mock_CBMessageBroker,
        mock_CBCloudLogger, mock_CBResponse, mock_Command_run,
        mock_Privileges_check_for_root_permissions
    ):
        sys.argv = [
            sys.argv[0],
            '--root', '/var/tmp/CB/projects/package@dist.arch',
            '--package', 'ROOT_HOME/cloud_builder_sources/projects/package',
            '--profile', 'dist.arch',
            '--request-id', 'uuid'
        ]
        log = Mock()
        response = Mock()
        mock_CBCloudLogger.return_value = log
        mock_CBResponse.return_value = response
        mock_Command_run.return_value.returncode = 0
        mock_Command_run.return_value.output = \
            'stdout-data\n{"resolved-packages": {"zypper":{"key":"val"}}}'
        mock_Command_run.return_value.error = 'stderr-data'
        mock_Path.which.return_value = 'kiwi-ng'
        run_script = dedent('''
            #!/bin/bash

            set -e

            function finish {
                for path in /proc /dev;do
                    mountpoint -q "$path" && umount "$path"
                done
            }

            trap finish EXIT

            mount -t proc proc /proc
            mount -t devtmpfs devtmpfs /dev

            pushd package
            if type -p build; then
                build --no-init --root /
            else
                obs-build --no-init --root /
            fi
        ''')

        with patch.dict('os.environ', {'HOME': 'ROOT_HOME'}):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value = MagicMock(spec=io.IOBase)
                file_handle = mock_open.return_value.__enter__.return_value
                main()

        mock_Privileges_check_for_root_permissions.assert_called_once_with()
        mock_Command_run.assert_called_once_with(
            [
                'kiwi-ng', '--profile', 'dist.arch',
                'image', 'info', '--description',
                'ROOT_HOME/cloud_builder_sources/projects/package',
                '--resolve-package-list'
            ], raise_on_error=False
        )
        mock_os_system.assert_called_once_with(' '.join(
            [
                'kiwi-ng', '--profile', 'dist.arch', '--logfile',
                '/var/tmp/CB/projects/package@dist.arch.prepare.log',
                'system', 'prepare', '--description',
                'ROOT_HOME/cloud_builder_sources/projects/package',
                '--allow-existing-root',
                '--root', '/var/tmp/CB/projects/package@dist.arch'
            ]
        ))
        mock_DataSync.assert_called_once_with(
            'ROOT_HOME/cloud_builder_sources/projects/package/',
            '/var/tmp/CB/projects/package@dist.arch/package/'
        )
        mock_DataSync.return_value.sync_data.assert_called_once_with(
            options=['-a', '-x']
        )
        assert mock_open.call_args_list == [
            call('/var/tmp/CB/projects/package@dist.arch.prepare.log', 'w'),
            call('/var/tmp/CB/projects/package@dist.arch.solver.json', 'w'),
            call('/var/tmp/CB/projects/package@dist.arch/run.sh', 'w')
        ]
        assert file_handle.write.call_args_list == [
            call('stdout-data\nstderr-data'),
            call('{\n    "resolved-packages": {\n        "zypper": {\n            "key": "val"\n        }\n    }\n}'),
            call(run_script)
        ]
        response.set_package_buildroot_response.assert_called_once_with(
            message='Buildroot ready for package build',
            response_code='build root setup succeeded',
            package='projects/package',
            log_file='/var/tmp/CB/projects/package@dist.arch.prepare.log',
            solver_file='/var/tmp/CB/projects/package@dist.arch.solver.json',
            build_root='/var/tmp/CB/projects/package@dist.arch',
            exit_code=0
        )
        log.response.assert_called_once_with(
            response, mock_CBMessageBroker.new.return_value
        )

    @patch('cloud_builder.cb_prepare.Privileges.check_for_root_permissions')
    @patch('cloud_builder.cb_prepare.CBCloudLogger')
    @patch('cloud_builder.cb_prepare.Path')
    @patch('cloud_builder.cb_prepare.DataSync')
    @patch('os.system')
    @patch('os.WEXITSTATUS')
    @patch('sys.exit')
    def test_main_solver_ok_prepare_failed(
        self, mock_sys_exit, mock_os_WEXITSTATUS, mock_os_system,
        mock_DataSync, mock_Path, mock_CBCloudLogger,
        mock_Privileges_check_for_root_permissions
    ):
        sys.argv = [
            sys.argv[0],
            '--root',
            '/some/abs/path/cloud_builder_sources/projects/package@dist.arch',
            '--package',
            '/some/abs/path/cloud_builder_sources/projects/package',
            '--profile', 'dist.arch',
            '--request-id', 'uuid',
            '--local'
        ]
        log = Mock()
        mock_CBCloudLogger.return_value = log
        mock_os_WEXITSTATUS.return_value = 1
        mock_Path.which.return_value = 'kiwi-ng'

        with patch.dict('os.environ', {'HOME': 'ROOT_HOME'}):
            main()

        mock_os_system.assert_called_once_with(' '.join(
            [
                'kiwi-ng', '--profile', 'dist.arch', '--debug',
                'system', 'prepare',
                '--description',
                '/some/abs/path/cloud_builder_sources/projects/package',
                '--allow-existing-root',
                '--root',
                '/some/abs/path/cloud_builder_sources/projects/'
                'package@dist.arch'
            ]
        ))
        assert not mock_DataSync.called

    @patch('cloud_builder.cb_prepare.Privileges.check_for_root_permissions')
    @patch('cloud_builder.cb_prepare.Command.run')
    @patch('cloud_builder.cb_prepare.CBResponse')
    @patch('cloud_builder.cb_prepare.CBCloudLogger')
    @patch('cloud_builder.cb_prepare.CBMessageBroker')
    @patch('cloud_builder.cb_prepare.Path')
    @patch('cloud_builder.cb_prepare.DataSync')
    @patch('os.system')
    @patch('os.WEXITSTATUS')
    @patch('sys.exit')
    def test_package_source_sync_failed(
        self, mock_sys_exit, mock_os_WEXITSTATUS, mock_os_system,
        mock_DataSync, mock_Path, mock_CBMessageBroker,
        mock_CBCloudLogger, mock_CBResponse, mock_Command_run,
        mock_Privileges_check_for_root_permissions
    ):
        sys.argv = [
            sys.argv[0],
            '--root', '/var/tmp/CB/projects/package@dist.arch',
            '--package', 'ROOT_HOME/cloud_builder_sources/projects/package',
            '--profile', 'dist.arch',
            '--request-id', 'uuid'
        ]
        log = Mock()
        response = Mock()
        mock_CBCloudLogger.return_value = log
        mock_CBResponse.return_value = response
        mock_Command_run.return_value.returncode = 0
        mock_os_WEXITSTATUS.return_value = 0
        mock_DataSync.side_effect = Exception('sync error')
        mock_Path.which.return_value = 'kiwi-ng'

        with patch.dict('os.environ', {'HOME': 'ROOT_HOME'}):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value = MagicMock(spec=io.IOBase)
                main()

        response.set_package_buildroot_response.assert_called_once_with(
            message='sync error',
            response_code='build root setup failed',
            package='projects/package',
            log_file='/var/tmp/CB/projects/package@dist.arch.prepare.log',
            solver_file='/var/tmp/CB/projects/package@dist.arch.solver.json',
            build_root='/var/tmp/CB/projects/package@dist.arch',
            exit_code=1
        )
        log.response.assert_called_once_with(
            response, mock_CBMessageBroker.new.return_value
        )
