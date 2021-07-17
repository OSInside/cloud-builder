from mock import patch

from cloud_builder.utils.display import CBDisplay


class TestCBDisplay:
    @patch('json.dumps')
    def test_print_json(self, mock_json_dumps):
        CBDisplay.print_json({'key': 'value'})
        mock_json_dumps.assert_called_once_with(
            {'key': 'value'}, sort_keys=True, indent=4
        )

    def test_print_raw(self):
        with patch('builtins.print') as mock_print:
            CBDisplay.print_raw('text')
            mock_print.assert_called_once_with('text')
