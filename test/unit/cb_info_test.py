import sys
import io
from pytest import raises
from mock import (
    patch, Mock, MagicMock, call
)

from cloud_builder.defaults import Defaults
from cloud_builder.cb_info import (
    main,
    handle_info_requests,
    lookup,
    get_result_modification_time,
    get_package_status,
    is_building
)


class TestCBInfo:
    def setup(self):
        sys.argv = [
            sys.argv[0]
        ]

    @patch('cloud_builder.cb_info.handle_info_requests')
    @patch('cloud_builder.cb_info.Privileges.check_for_root_permissions')
    @patch('cloud_builder.cb_info.BlockingScheduler')
    def test_main_normal_runtime(
        self, mock_BlockingScheduler,
        mock_Privileges_check_for_root_permissions,
        mock_handle_info_requests
    ):
        info_scheduler = Mock()
        mock_BlockingScheduler.return_value = info_scheduler
        main()
        mock_Privileges_check_for_root_permissions.assert_called_once_with()
        mock_handle_info_requests.assert_called_once_with(
            5000
        )
        mock_BlockingScheduler.assert_called_once_with()
        info_scheduler.start.assert_called_once_with()

    @patch('cloud_builder.cb_info.Privileges.check_for_root_permissions')
    @patch('cloud_builder.cb_info.Defaults')
    @patch('sys.exit')
    def test_main_poll_timeout_greater_than_update_interval(
        self, mock_sys_exit, mock_Defaults,
        mock_Privileges_check_for_root_permissions,
    ):
        sys.argv = [
            sys.argv[0], '--poll-timeout', '20000', '--update-interval', '10'
        ]
        main()
        mock_sys_exit.assert_called_once_with(1)

    @patch('cloud_builder.cb_info.lookup')
    @patch('cloud_builder.cb_info.CBCloudLogger')
    @patch('cloud_builder.cb_info.CBMessageBroker')
    @patch('cloud_builder.cb_info.CBIdentity')
    def test_handle_info_requests(
        self, mock_CBIdentity, mock_CBMessageBroker,
        mock_CBCloudLogger, mock_lookup
    ):
        log = Mock()
        request = {
            'arch': 'x86_64',
            'dist': 'TW',
            'package': 'vim',
            'request_id': 'uuid',
            'schema_version': 0.1
        }
        broker = Mock()
        broker_read_return = [
            [Mock(value=request)]
        ]

        def broker_read_call(**args):
            return broker_read_return.pop()

        broker.read.side_effect = broker_read_call

        broker.validate_info_request.return_value = request
        mock_CBCloudLogger.return_value = log
        mock_CBMessageBroker.new.return_value = broker

        with raises(IndexError):
            handle_info_requests(5000)

        assert broker.read.call_args_list[0] == call(
            topic='cb-info-request',
            group=mock_CBIdentity.get_external_ip.return_value,
            timeout_ms=5000
        )
        mock_lookup.assert_called_once_with(
            'vim', 'x86_64', 'TW', 'uuid', broker
        )
        broker.close.assert_called_once_with()

    @patch('cloud_builder.cb_info.CBCloudLogger')
    @patch('cloud_builder.cb_info.CBInfoResponse')
    @patch('cloud_builder.cb_info.get_result_modification_time')
    @patch('cloud_builder.cb_info.is_building')
    @patch('cloud_builder.cb_info.get_package_status')
    @patch('os.path.isfile')
    def test_lookup(
        self, mock_os_path_isfile, mock_get_package_status,
        mock_is_building, mock_get_result_modification_time,
        mock_CBInfoResponse, mock_CBCloudLogger
    ):
        mock_os_path_isfile.return_value = True
        mock_get_result_modification_time.return_value = 'utctime'
        log = Mock()
        log.get_id.return_value = 'CBRun:18.193.45.127:...'
        response = Mock()
        mock_CBCloudLogger.return_value = log
        mock_CBInfoResponse.return_value = response
        broker = Mock()
        broker.validate_package_response.return_value = {
            'binary_packages': [],
            'prepare_log_file': 'prepare_log_file',
            'log_file': 'log_file',
            'solver_file': 'solver_file',
            'response_code': 'response_code'
        }

        with patch('builtins.open', create=True):
            lookup('package', 'arch', 'dist', 'uuid', broker)

        broker.acknowledge.assert_called_once_with()
        response.set_info_response_result.assert_called_once_with(
            broker.validate_package_response.return_value['binary_packages'],
            broker.validate_package_response.return_value['prepare_log_file'],
            broker.validate_package_response.return_value['log_file'],
            broker.validate_package_response.return_value['solver_file'],
            mock_get_result_modification_time.return_value,
            mock_get_package_status.return_value
        )
        log.info_response.assert_called_once_with(response, broker)

    @patch('cloud_builder.cb_info.datetime')
    @patch('os.path.getmtime')
    def test_get_result_modification_time(
        self, mock_os_path_getmtime, mock_datetime
    ):
        get_result_modification_time('filename')
        mock_datetime.utcfromtimestamp.assert_called_once_with(
            mock_os_path_getmtime.return_value
        )

    def test_get_package_status(self):
        status_flags = Defaults.get_status_flags()
        assert get_package_status('package build succeeded') == \
            status_flags.package_build_succeeded
        assert get_package_status('package build failed') == \
            status_flags.package_build_failed
        assert get_package_status('package build running') == \
            status_flags.package_build_running
        assert get_package_status('foo') == \
            'unknown'

    @patch('psutil.pid_exists')
    def test_is_building(self, mock_psutil_pid_exists):
        mock_psutil_pid_exists.return_value = False
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            assert is_building('pidfile') is False

        mock_psutil_pid_exists.return_value = True
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            assert is_building('pidfile') is True
