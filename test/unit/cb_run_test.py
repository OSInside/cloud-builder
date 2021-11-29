import sys
import io
from mock import (
    patch, Mock, call, MagicMock
)

from cloud_builder.cb_run import main


class TestCBRun:
    def setup(self):
        sys.argv = [
            sys.argv[0]
        ]

    @patch('cloud_builder.cb_run.CBRepository')
    @patch('cloud_builder.cb_run.Path')
    @patch('cloud_builder.cb_run.Privileges.check_for_root_permissions')
    @patch('cloud_builder.cb_run.Command.run')
    @patch('cloud_builder.cb_run.CBResponse')
    @patch('cloud_builder.cb_run.CBCloudLogger')
    @patch('cloud_builder.cb_run.CBMessageBroker')
    @patch('os.system')
    @patch('os.rename')
    @patch('os.walk')
    @patch('sys.exit')
    def test_main_clean_root_runtime(
        self, mock_sys_exit, mock_os_walk, mock_os_rename, mock_os_system,
        mock_CBMessageBroker, mock_CBCloudLogger, mock_CBResponse,
        mock_Command_run, mock_Privileges_check_for_root_permissions,
        mock_Path, mock_CBRepository
    ):
        sys.argv = [
            sys.argv[0],
            '--root', '/var/tmp/CB/projects/package@dist.arch',
            '--request-id', 'uuid',
            '--repo-path', 'projects/MS/TW',
            '--repo-server', '192.168.100.1',
            '--ssh-user', 'cb-collect',
            '--ssh-pkey', 'path/to/pkey',
            '--clean'
        ]
        mock_os_walk.return_value = [
            (
                '/var/tmp/CB/projects/package@dist.arch/'
                'package@dist.arch.binaries',
                [],
                ['binaries']
            )
        ]
        log = Mock()
        response = Mock()
        mock_CBCloudLogger.return_value = log
        mock_CBResponse.return_value = response
        mock_os_system.return_value = 0
        mock_Command_run.return_value.output = 'binaries'
        mock_Command_run.return_value.error = 'sync failed'
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            main()
        mock_Privileges_check_for_root_permissions.assert_called_once_with()
        mock_os_system.assert_called_once_with(
            'chroot /var/tmp/CB/projects/package@dist.arch bash /run.sh'
        )
        mock_open.assert_called_once_with(
            '/var/tmp/CB/projects/package@dist.arch/'
            'package@dist.arch.binaries/projects/MS/TW/'
            '.updaterepo', 'w'
        )
        file_handle.write.assert_called_once_with(
            mock_CBRepository.return_value.get_repo_meta.return_value.repo_type
        )
        assert mock_Command_run.call_args_list == [
            call(
                [
                    'find',
                    '/var/tmp/CB/projects/package@dist.arch/home/abuild',
                    '/var/tmp/CB/projects/package@dist.arch/'
                    'usr/src/packages/DEBS',
                    '-type', 'f',
                    '-name', '*.rpm', '-or', '-name', '*.deb'
                ], raise_on_error=False
            ),
            call(
                [
                    'rsync', '-av', '-e',
                    'ssh -i path/to/pkey -o StrictHostKeyChecking=accept-new',
                    '/var/tmp/CB/projects/package@dist.arch/'
                    'package@dist.arch.binaries/',
                    'cb-collect@192.168.100.1:/srv/www/projects'
                ], raise_on_error=False
            )
        ]
        assert mock_Path.create.call_args_list == [
            call(
                '/var/tmp/CB/projects/package@dist.arch.binaries/'
                'projects/MS/TW'
            ),
            call(
                '/var/tmp/CB/projects/package@dist.arch'
            )
        ]
        assert mock_Path.wipe.call_args_list == [
            call(
                '/var/tmp/CB/projects/package@dist.arch.binaries/'
                'projects/MS/TW'
            ),
            call('/var/tmp/CB/projects/package@dist.arch')
        ]

        assert mock_os_rename.call_args_list == [
            call(
                'binaries',
                mock_CBRepository.return_value.
                get_repo_meta.return_value.repo_file
            ),
            call(
                '/var/tmp/CB/projects/package@dist.arch.binaries',
                '/var/tmp/CB/projects/package@dist.arch/'
                'package@dist.arch.binaries'
            )
        ]
        response.set_package_build_response.assert_called_once_with(
            message='Package build finished',
            response_code='package binaries sync failed',
            package='projects/package',
            prepare_log_file='/var/tmp/CB/projects/'
            'package@dist.arch.prepare.log',
            log_file='/var/tmp/CB/projects/package@dist.arch.build.log',
            solver_file='/var/tmp/CB/projects/package@dist.arch.solver.json',
            binary_packages=[
                '/var/tmp/CB/projects/package@dist.arch/'
                'package@dist.arch.binaries/binaries'
            ],
            exit_code=1
        )
        log.response.assert_called_once_with(
            response, mock_CBMessageBroker.new.return_value,
            '/var/tmp/CB/projects/package@dist.arch.result.yml'
        )

    @patch('cloud_builder.cb_run.CBRepository')
    @patch('cloud_builder.cb_run.Path')
    @patch('cloud_builder.cb_run.Privileges.check_for_root_permissions')
    @patch('cloud_builder.cb_run.Command.run')
    @patch('cloud_builder.cb_run.CBCloudLogger')
    @patch('os.system')
    @patch('os.rename')
    @patch('os.walk')
    @patch('sys.exit')
    def test_main_local_keep_root_runtime(
        self, mock_sys_exit, mock_os_walk, mock_os_rename, mock_os_system,
        mock_CBCloudLogger, mock_Command_run,
        mock_Privileges_check_for_root_permissions,
        mock_Path, mock_CBRepository
    ):
        sys.argv = [
            sys.argv[0],
            '--root', '/var/tmp/CB/projects/package@dist.arch',
            '--request-id', 'uuid',
            '--local'
        ]
        log = Mock()
        mock_CBCloudLogger.return_value = log
        mock_os_system.return_value = 0
        mock_Command_run.return_value.output = 'binaries'
        main()

        mock_Path.create.assert_called_once_with(
            '/var/tmp/CB/projects/package@dist.arch.binaries'
        )
        mock_Path.wipe.assert_called_once_with(
            '/var/tmp/CB/projects/package@dist.arch.binaries'
        )
        assert mock_os_rename.call_args_list == [
            call(
                'binaries',
                mock_CBRepository.return_value.
                get_repo_meta.return_value.repo_file
            ),
            call(
                '/var/tmp/CB/projects/package@dist.arch.binaries',
                '/var/tmp/CB/projects/package@dist.arch/'
                'package@dist.arch.binaries'
            )
        ]

    @patch('cloud_builder.cb_run.Privileges.check_for_root_permissions')
    @patch('cloud_builder.cb_run.Command.run')
    @patch('cloud_builder.cb_run.CBResponse')
    @patch('cloud_builder.cb_run.CBCloudLogger')
    @patch('cloud_builder.cb_run.CBMessageBroker')
    @patch('os.system')
    @patch('sys.exit')
    def test_main_run_package_build_failed(
        self, mock_sys_exit, mock_os_system, mock_CBMessageBroker,
        mock_CBCloudLogger, mock_CBResponse, mock_Command_run,
        mock_Privileges_check_for_root_permissions
    ):
        sys.argv = [
            sys.argv[0],
            '--root', '/var/tmp/CB/projects/package@dist.arch',
            '--request-id', 'uuid'
        ]
        response = Mock()
        mock_CBResponse.return_value = response
        mock_os_system.return_value = 0xffff
        mock_Command_run.return_value.output = ''
        main()
        response.set_package_build_response.assert_called_once_with(
            message='Package build finished',
            response_code='package build failed',
            package='projects/package',
            prepare_log_file='/var/tmp/CB/projects/'
            'package@dist.arch.prepare.log',
            log_file='/var/tmp/CB/projects/package@dist.arch.build.log',
            solver_file='/var/tmp/CB/projects/package@dist.arch.solver.json',
            binary_packages=[],
            exit_code=0xff
        )

    @patch('cloud_builder.cb_run.Privileges.check_for_root_permissions')
    @patch('cloud_builder.cb_run.Command.run')
    @patch('cloud_builder.cb_run.CBResponse')
    @patch('cloud_builder.cb_run.CBCloudLogger')
    @patch('cloud_builder.cb_run.CBMessageBroker')
    @patch('os.system')
    @patch('os.rename')
    @patch('os.walk')
    @patch('sys.exit')
    def test_main_run_package_build_succeeded_but_no_binaries_found(
        self, mock_sys_exit, mock_os_walk, mock_os_rename, mock_os_system,
        mock_CBMessageBroker, mock_CBCloudLogger, mock_CBResponse,
        mock_Command_run, mock_Privileges_check_for_root_permissions
    ):
        sys.argv = [
            sys.argv[0],
            '--root', '/var/tmp/CB/projects/package@dist.arch',
            '--request-id', 'uuid'
        ]
        mock_os_walk.return_value = []
        response = Mock()
        mock_CBResponse.return_value = response
        mock_os_system.return_value = 0
        mock_Command_run.return_value.output = ''
        main()
        response.set_package_build_response.assert_called_once_with(
            message='Package build finished',
            response_code='package build failed, no binaries found',
            package='projects/package',
            prepare_log_file='/var/tmp/CB/projects/'
            'package@dist.arch.prepare.log',
            log_file='/var/tmp/CB/projects/package@dist.arch.build.log',
            solver_file='/var/tmp/CB/projects/package@dist.arch.solver.json',
            binary_packages=[],
            exit_code=1
        )
