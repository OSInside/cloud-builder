from mock import patch

from cloud_builder.utils.repository import (
    CBRepository, repo_metadata
)


class TestCBRepository:
    def setup(self):
        self.repo_rpm = CBRepository('binary.rpm')
        self.repo_unknown = CBRepository('binary')

    def test_get_repo_type(self):
        assert self.repo_rpm.get_repo_type() == 'rpm'
        assert self.repo_unknown.get_repo_type() is None

    @patch('cloud_builder.utils.repository.Path')
    def test_get_repo_meta_arch_rpm_binary(self, mock_Path):
        meta = CBRepository('binary.x86_64.rpm').get_repo_meta('base_repo_path')
        assert meta == repo_metadata(
            repo_type='rpm',
            repo_path='base_repo_path/x86_64',
            repo_file='base_repo_path/x86_64/binary.x86_64.rpm'
        )

    @patch('cloud_builder.utils.repository.Path')
    def test_get_repo_meta_noarch_rpm_binary(self, mock_Path):
        meta = CBRepository('binary.noarch.rpm').get_repo_meta('base_repo_path')
        assert meta == repo_metadata(
            repo_type='rpm',
            repo_path='base_repo_path/noarch',
            repo_file='base_repo_path/noarch/binary.noarch.rpm'
        )

    @patch('cloud_builder.utils.repository.Path')
    def test_get_repo_meta_src_rpm_binary(self, mock_Path):
        meta = CBRepository('binary.src.rpm').get_repo_meta('base_repo_path')
        assert meta == repo_metadata(
            repo_type='rpm',
            repo_path='base_repo_path/src',
            repo_file='base_repo_path/src/binary.src.rpm'
        )

    @patch('cloud_builder.utils.repository.Path')
    def test_get_repo_meta_unknown_binary(self, mock_Path):
        meta = CBRepository('binary').get_repo_meta('base_repo_path')
        assert meta == repo_metadata(
            repo_type='unknown',
            repo_path='unknown',
            repo_file='base_repo_path/binary'
        )
