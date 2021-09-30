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
    lookup_package,
    lookup_image,
    get_result_modification_time,
    get_package_status,
    get_image_status,
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
    @patch('cloud_builder.cb_info.CBCloudLogger')
    def test_main_normal_runtime(
        self, mock_CBCloudLogger, mock_BlockingScheduler,
        mock_Privileges_check_for_root_permissions,
        mock_handle_info_requests
    ):
        info_scheduler = Mock()
        mock_BlockingScheduler.return_value = info_scheduler
        main()
        mock_Privileges_check_for_root_permissions.assert_called_once_with()
        mock_handle_info_requests.assert_called_once_with(
            5000, mock_CBCloudLogger.return_value
        )
        mock_BlockingScheduler.assert_called_once_with()
        info_scheduler.start.assert_called_once_with()

    @patch('cloud_builder.cb_info.Privileges.check_for_root_permissions')
    @patch('cloud_builder.cb_info.Defaults')
    @patch('sys.exit')
    @patch('cloud_builder.cb_info.CBCloudLogger')
    def test_main_poll_timeout_greater_than_update_interval(
        self, mock_CBCloudLogger, mock_sys_exit, mock_Defaults,
        mock_Privileges_check_for_root_permissions,
    ):
        sys.argv = [
            sys.argv[0], '--poll-timeout', '20000', '--update-interval', '10'
        ]
        main()
        mock_sys_exit.assert_called_once_with(1)

    @patch('cloud_builder.cb_info.lookup_image')
    @patch('cloud_builder.cb_info.CBCloudLogger')
    @patch('cloud_builder.cb_info.CBMessageBroker')
    @patch('cloud_builder.cb_info.CBIdentity')
    def test_handle_info_requests_for_image_build(
        self, mock_CBIdentity, mock_CBMessageBroker,
        mock_CBCloudLogger, mock_lookup_image
    ):
        log = Mock()
        request = {
            'image': {
                'arch': 'x86_64',
                'selection': 'selection'
            },
            'project': 'myimage',
            'request_id': 'uuid',
            'schema_version': 0.2
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
            handle_info_requests(5000, log)

        assert broker.read.call_args_list[0] == call(
            topic='cb-info-request',
            group=mock_CBIdentity.get_external_ip.return_value,
            timeout_ms=5000
        )
        mock_lookup_image.assert_called_once_with(
            'myimage', 'x86_64', 'selection', 'uuid', broker, log
        )
        broker.close.assert_called_once_with()

    @patch('cloud_builder.cb_info.lookup_package')
    @patch('cloud_builder.cb_info.CBCloudLogger')
    @patch('cloud_builder.cb_info.CBMessageBroker')
    @patch('cloud_builder.cb_info.CBIdentity')
    def test_handle_info_requests_for_package_build(
        self, mock_CBIdentity, mock_CBMessageBroker,
        mock_CBCloudLogger, mock_lookup_package
    ):
        log = Mock()
        request = {
            'package': {
                'arch': 'x86_64',
                'dist': 'TW',
            },
            'project': 'vim',
            'request_id': 'uuid',
            'schema_version': 0.2
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
            handle_info_requests(5000, log)

        assert broker.read.call_args_list[0] == call(
            topic='cb-info-request',
            group=mock_CBIdentity.get_external_ip.return_value,
            timeout_ms=5000
        )
        mock_lookup_package.assert_called_once_with(
            'vim', 'x86_64', 'TW', 'uuid', broker, log
        )
        broker.close.assert_called_once_with()

    @patch('cloud_builder.cb_info.CBCloudLogger')
    @patch('cloud_builder.cb_info.CBInfoResponse')
    @patch('cloud_builder.cb_info.get_result_modification_time')
    @patch('cloud_builder.cb_info.is_building')
    @patch('cloud_builder.cb_info.get_image_status')
    @patch('os.path.isfile')
    def test_lookup_image(
        self, mock_os_path_isfile, mock_get_image_status,
        mock_is_building, mock_get_result_modification_time,
        mock_CBInfoResponse, mock_CBCloudLogger
    ):
        mock_os_path_isfile.return_value = True
        mock_get_result_modification_time.return_value = 'utctime'
        log = Mock()
        log.get_id.return_value = 'CBImage:18.193.45.127:...'
        response = Mock()
        mock_CBCloudLogger.return_value = log
        mock_CBInfoResponse.return_value = response
        broker = Mock()
        broker.validate_build_response.return_value = {
            'image': {
                'binary_packages': [],
                'log_file': '/var/tmp/CB/image@selection.arch.build.log',
                'solver_file': '/var/tmp/CB/image@selection.arch.solver.json',
            },
            'response_code': 'response_code'
        }

        with patch('builtins.open', create=True):
            lookup_image('image', 'arch', 'selection', 'uuid', broker, log)

        broker.acknowledge.assert_called_once_with()
        result = broker.validate_build_response.return_value
        response.set_image_info_response_result.assert_called_once_with(
            result['image']['binary_packages'],
            result['image']['log_file'],
            result['image']['solver_file'],
            mock_get_result_modification_time.return_value,
            mock_get_image_status.return_value
        )
        log.info_response.assert_called_once_with(response, broker)

    @patch('cloud_builder.cb_info.CBCloudLogger')
    @patch('cloud_builder.cb_info.CBInfoResponse')
    @patch('cloud_builder.cb_info.get_result_modification_time')
    @patch('cloud_builder.cb_info.is_building')
    @patch('cloud_builder.cb_info.get_package_status')
    @patch('os.path.isfile')
    def test_lookup_package(
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
        broker.validate_build_response.return_value = {
            'package': {
                'binary_packages': [],
                'prepare_log_file': '/var/tmp/CB/package@dist.arch.prepare.log',
                'log_file': '/var/tmp/CB/package@dist.arch.build.log',
                'solver_file': '/var/tmp/CB/package@dist.arch.solver.json',
            },
            'response_code': 'response_code'
        }

        with patch('builtins.open', create=True):
            lookup_package('package', 'arch', 'dist', 'uuid', broker, log)

        broker.acknowledge.assert_called_once_with()
        result = broker.validate_build_response.return_value
        response.set_package_info_response_result.assert_called_once_with(
            result['package']['binary_packages'],
            result['package']['prepare_log_file'],
            result['package']['log_file'],
            result['package']['solver_file'],
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
        assert get_package_status('foo') == \
            'unknown'

    def test_get_image_status(self):
        status_flags = Defaults.get_status_flags()
        assert get_image_status('image build succeeded') == \
            status_flags.image_build_succeeded
        assert get_image_status('image build failed') == \
            status_flags.image_build_failed
        assert get_image_status('foo') == \
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
