from mock import (
    patch, call, Mock
)

from cloud_builder.utils.git import CBGit


class TestCBGit:
    def setup(self):
        self.git = CBGit('clone_uri', 'checkout_path')

    @patch('cloud_builder.utils.git.Command.run')
    def test_clone(self, mock_Command_run):
        self.git.clone(branch='main')
        assert mock_Command_run.call_args_list == [
            call(['git', 'clone', 'clone_uri', 'checkout_path']),
            call(['git', '-C', 'checkout_path', 'checkout', 'main'])
        ]

    @patch('cloud_builder.utils.git.Command.run')
    def test_pull(self, mock_Command_run):
        self.git.pull()
        mock_Command_run.assert_called_once_with(
            ['git', '-C', 'checkout_path', 'pull']
        )

    @patch('cloud_builder.utils.git.Command.run')
    def test_fetch(self, mock_Command_run):
        self.git.fetch()
        mock_Command_run.assert_called_once_with(
            ['git', '-C', 'checkout_path', 'fetch', '--all']
        )

    @patch('cloud_builder.utils.git.Command.run')
    def test_get_changed_files(self, mock_Command_run):
        command_out = Mock()
        command_out.output = 'file1\nfile2\nfile3'
        mock_Command_run.return_value = command_out
        assert self.git.get_changed_files() == [
            'file1', 'file2', 'file3'
        ]
        mock_Command_run.assert_called_once_with(
            [
                'git', '-C', 'checkout_path', 'diff',
                '--name-only', 'origin/master'
            ]
        )
