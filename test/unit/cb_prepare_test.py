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
    def test_main_normal_runtime(
        self, mock_DataSync, mock_Path, mock_CBMessageBroker,
        mock_CBCloudLogger, mock_CBResponse, mock_Command_run,
        mock_Privileges_check_for_root_permissions
    ):
        sys.argv = [
            sys.argv[0],
            '--root', '/var/tmp/CB',
            '--package', 'ROOT_HOME/cloud_builder_sources/projects/package',
            '--profile', 'dist.arch',
            '--request-id', 'uuid'
        ]
        log = Mock()
        response = Mock()
        mock_CBCloudLogger.return_value = log
        mock_CBResponse.return_value = response
        mock_Command_run.return_value.returncode = 0
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
            build --no-init --root /
        ''')

        with patch.dict('os.environ', {'HOME': 'ROOT_HOME'}):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value = MagicMock(spec=io.IOBase)
                file_handle = mock_open.return_value.__enter__.return_value
                main()

        mock_Privileges_check_for_root_permissions.assert_called_once_with()
        mock_Path.wipe.assert_called_once_with(
            '/var/tmp/CB/projects/package@dist.arch.prepare.log'
        )
        assert mock_Command_run.call_args_list == [
            call(
                [
                    'kiwi-ng', '--logfile',
                    '/var/tmp/CB/projects/package@dist.arch.prepare.log',
                    '--profile', 'dist.arch',
                    'image', 'info', '--description',
                    'ROOT_HOME/cloud_builder_sources/projects/package',
                    '--resolve-package-list'
                ], raise_on_error=False
            ),
            call(
                [
                    'kiwi-ng', '--logfile',
                    '/var/tmp/CB/projects/package@dist.arch.prepare.log',
                    '--profile', 'dist.arch',
                    'system', 'prepare', '--description',
                    'ROOT_HOME/cloud_builder_sources/projects/package',
                    '--allow-existing-root',
                    '--root', '/var/tmp/CB/projects/package@dist.arch'
                ], raise_on_error=False
            )
        ]
        mock_DataSync.assert_called_once_with(
            'ROOT_HOME/cloud_builder_sources/projects/package/',
            '/var/tmp/CB/projects/package@dist.arch/package/'
        )
        mock_DataSync.return_value.sync_data.assert_called_once_with(
            options=['-a', '-x']
        )
        assert mock_open.call_args_list == [
            call('/var/tmp/CB/projects/package@dist.arch.solver.json', 'w'),
            call('/var/tmp/CB/projects/package@dist.arch/run.sh', 'w')
        ]
        file_handle.write.assert_called_once_with(run_script)
        response.set_package_buildroot_response.assert_called_once_with(
            message='Buildroot ready for package build',
            response_code='build root setup succeeded',
            package='package',
            log_file='/var/tmp/CB/projects/package@dist.arch.prepare.log',
            solver_file='/var/tmp/CB/projects/package@dist.arch.solver.json',
            build_root='/var/tmp/CB/projects/package@dist.arch',
            exit_code=0
        )
        log.response.assert_called_once_with(
            response, mock_CBMessageBroker.new.return_value
        )

    @patch('cloud_builder.cb_prepare.Privileges.check_for_root_permissions')
    @patch('cloud_builder.cb_prepare.Command.run')
    @patch('cloud_builder.cb_prepare.CBResponse')
    @patch('cloud_builder.cb_prepare.CBCloudLogger')
    @patch('cloud_builder.cb_prepare.CBMessageBroker')
    @patch('cloud_builder.cb_prepare.Path')
    @patch('cloud_builder.cb_prepare.DataSync')
    def test_main_solver_ok_prepare_failed(
        self, mock_DataSync, mock_Path, mock_CBMessageBroker,
        mock_CBCloudLogger, mock_CBResponse, mock_Command_run,
        mock_Privileges_check_for_root_permissions
    ):
        sys.argv = [
            sys.argv[0],
            '--root', '/var/tmp/CB',
            '--package', 'ROOT_HOME/cloud_builder_sources/projects/package',
            '--profile', 'dist.arch',
            '--request-id', 'uuid'
        ]
        log = Mock()
        response = Mock()
        mock_CBCloudLogger.return_value = log
        mock_CBResponse.return_value = response
        mock_Command_run.return_value.returncode = 1
        mock_Command_run.return_value.output = '{\nsolver_data\n}'
        mock_Path.which.return_value = 'kiwi-ng'

        with patch.dict('os.environ', {'HOME': 'ROOT_HOME'}):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value = MagicMock(spec=io.IOBase)
                file_handle = mock_open.return_value.__enter__.return_value
                main()

        mock_open.assert_called_once_with(
            '/var/tmp/CB/projects/package@dist.arch.solver.json', 'w'
        )
        assert file_handle.write.call_args_list == [
            call('{'), call('\n'),
            call('solver_data'), call('\n'),
            call('}'), call('\n')
        ]
        response.set_package_buildroot_response.assert_called_once_with(
            message='Failed in kiwi stage, see logfile for details',
            response_code='build root setup failed',
            package='package',
            log_file='/var/tmp/CB/projects/package@dist.arch.prepare.log',
            solver_file='/var/tmp/CB/projects/package@dist.arch.solver.json',
            build_root='/var/tmp/CB/projects/package@dist.arch',
            exit_code=1
        )
        log.response.assert_called_once_with(
            response, mock_CBMessageBroker.new.return_value
        )

    @patch('cloud_builder.cb_prepare.Privileges.check_for_root_permissions')
    @patch('cloud_builder.cb_prepare.Command.run')
    @patch('cloud_builder.cb_prepare.CBResponse')
    @patch('cloud_builder.cb_prepare.CBCloudLogger')
    @patch('cloud_builder.cb_prepare.CBMessageBroker')
    @patch('cloud_builder.cb_prepare.Path')
    @patch('cloud_builder.cb_prepare.DataSync')
    def test_package_source_sync_failed(
        self, mock_DataSync, mock_Path, mock_CBMessageBroker,
        mock_CBCloudLogger, mock_CBResponse, mock_Command_run,
        mock_Privileges_check_for_root_permissions
    ):
        sys.argv = [
            sys.argv[0],
            '--root', '/var/tmp/CB',
            '--package', 'ROOT_HOME/cloud_builder_sources/projects/package',
            '--profile', 'dist.arch',
            '--request-id', 'uuid'
        ]
        log = Mock()
        response = Mock()
        mock_CBCloudLogger.return_value = log
        mock_CBResponse.return_value = response
        mock_Command_run.return_value.returncode = 0
        mock_DataSync.side_effect = Exception('sync error')
        mock_Path.which.return_value = 'kiwi-ng'

        with patch.dict('os.environ', {'HOME': 'ROOT_HOME'}):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value = MagicMock(spec=io.IOBase)
                main()

        response.set_package_buildroot_response.assert_called_once_with(
            message='sync error',
            response_code='build root setup failed',
            package='package',
            log_file='/var/tmp/CB/projects/package@dist.arch.prepare.log',
            solver_file='/var/tmp/CB/projects/package@dist.arch.solver.json',
            build_root='/var/tmp/CB/projects/package@dist.arch',
            exit_code=1
        )
        log.response.assert_called_once_with(
            response, mock_CBMessageBroker.new.return_value
        )
