from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from csob_ceb_bc.downloads.manager import DownloadManager
from csob_ceb_bc.models import (
    DownloadFile,
    DownloadFileStatus,
    DownloadFileType,
    DownloadFilter,
)
from csob_ceb_bc.state.sqlite_repo import SqliteStateRepository


@pytest.fixture
def repo(tmp_path: Path):
    return SqliteStateRepository(f"sqlite:///{tmp_path}/state.db")


def test_profile_key_includes_contract_and_filter():
    mgr = DownloadManager(
        contract_number="123456",
        client_app_guid="guid",
        cert_fingerprint="fp",
        environment="production",
        soap=MagicMock(),
        rest=MagicMock(),
        state=MagicMock(),
    )
    key = mgr._profile_key(DownloadFilter(file_types=[DownloadFileType.VYPIS]))
    assert "123456" in key
    assert "VYPIS" in key
    assert "production" in key


def test_cursor_not_advanced_when_file_status_r(repo: SqliteStateRepository, tmp_path: Path):
    soap = MagicMock()
    rest = MagicMock()
    soap.get_download_file_list_v4.return_value = MagicMock(
        query_timestamp=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        files=[
            DownloadFile(
                filename="stmt.pdf",
                type=DownloadFileType.VYPIS,
                format="PDF",
                creation_date_time=datetime(2025, 1, 14, 9, 0, 0, tzinfo=timezone.utc),
                size=1024,
                status=DownloadFileStatus.R,
                url=None,
                upload_file_hash=None,
            )
        ],
    )
    mgr = DownloadManager(
        contract_number="123456",
        client_app_guid="guid",
        cert_fingerprint="fp",
        environment="production",
        soap=soap,
        rest=rest,
        state=repo,
    )
    mgr.download_new_files(DownloadFilter(file_types=[DownloadFileType.VYPIS]), tmp_path)
    key = mgr._profile_key(DownloadFilter(file_types=[DownloadFileType.VYPIS]))
    assert repo.get_profile_cursor(key) is None
