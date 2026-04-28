from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from csob_ceb_bc.downloads.manager import DownloadManager
from csob_ceb_bc.metrics import MetricsCollector
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


def test_profile_key_is_sha256():
    mgr = DownloadManager(
        contract_number="123456",
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        cert_fingerprint="fp",
        environment="production",
        soap=MagicMock(),
        rest=MagicMock(),
        state=MagicMock(),
    )
    key = mgr._profile_key(DownloadFilter(file_types=[DownloadFileType.VYPIS]))
    assert len(key) == 64
    key2 = mgr._profile_key(DownloadFilter(file_types=[DownloadFileType.VYPIS]))
    assert key == key2
    key3 = mgr._profile_key(DownloadFilter())
    assert key != key3


@pytest.mark.asyncio
async def test_cursor_not_advanced_when_file_status_r(repo: SqliteStateRepository, tmp_path: Path):
    soap = MagicMock()
    rest = MagicMock()
    soap.get_download_file_list_v4 = AsyncMock(
        return_value=MagicMock(
            query_timestamp=datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
            files=[
                DownloadFile(
                    filename="stmt.pdf",
                    type=DownloadFileType.VYPIS,
                    format="PDF",
                    creation_date_time=datetime(2025, 1, 14, 9, 0, 0, tzinfo=UTC),
                    size=1024,
                    status=DownloadFileStatus.R,
                    url=None,
                    upload_file_hash=None,
                )
            ],
        )
    )
    mgr = DownloadManager(
        contract_number="123456",
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        cert_fingerprint="fp",
        environment="production",
        soap=soap,
        rest=rest,
        state=repo,
    )
    await mgr.download_new_files(DownloadFilter(file_types=[DownloadFileType.VYPIS]), tmp_path)
    key = mgr._profile_key(DownloadFilter(file_types=[DownloadFileType.VYPIS]))
    assert repo.get_profile_cursor(key) is None


@pytest.mark.asyncio
async def test_cursor_advanced_when_all_downloaded(repo: SqliteStateRepository, tmp_path: Path):
    soap = MagicMock()
    rest = MagicMock()
    rest.download_to_file = AsyncMock()
    ts = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
    soap.get_download_file_list_v4 = AsyncMock(
        return_value=MagicMock(
            query_timestamp=ts,
            files=[
                DownloadFile(
                    filename="stmt.pdf",
                    type=DownloadFileType.VYPIS,
                    format="PDF",
                    creation_date_time=datetime(2025, 1, 14, 9, 0, 0, tzinfo=UTC),
                    size=1024,
                    status=DownloadFileStatus.D,
                    url="https://example.com/stmt.pdf",
                    upload_file_hash=None,
                )
            ],
        )
    )
    mgr = DownloadManager(
        contract_number="123456",
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        cert_fingerprint="fp",
        environment="production",
        soap=soap,
        rest=rest,
        state=repo,
    )
    result = await mgr.download_new_files(
        DownloadFilter(file_types=[DownloadFileType.VYPIS]), tmp_path
    )
    key = mgr._profile_key(DownloadFilter(file_types=[DownloadFileType.VYPIS]))
    assert repo.get_profile_cursor(key) == ts
    assert len(result.downloaded) == 1
    assert result.cursor_advanced is True
    assert result.has_pending_files is False
    rest.download_to_file.assert_awaited_once()


@pytest.mark.asyncio
async def test_download_retryable_rest_error_raised(repo: SqliteStateRepository, tmp_path: Path):
    from csob_ceb_bc.errors import CsobBCHttpError

    soap = MagicMock()
    rest = MagicMock()
    ts = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
    soap.get_download_file_list_v4 = AsyncMock(
        return_value=MagicMock(
            query_timestamp=ts,
            files=[
                DownloadFile(
                    filename="stmt.pdf",
                    type=DownloadFileType.VYPIS,
                    format="PDF",
                    creation_date_time=datetime(2025, 1, 14, 9, 0, 0, tzinfo=UTC),
                    size=1024,
                    status=DownloadFileStatus.D,
                    url="https://example.com/stmt.pdf",
                    upload_file_hash=None,
                )
            ],
        )
    )
    rest.download_to_file = AsyncMock(
        side_effect=CsobBCHttpError(
            "Server Error", operation="download", permanent=False, retryable=True
        )
    )
    mgr = DownloadManager(
        contract_number="123456",
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        cert_fingerprint="fp",
        environment="production",
        soap=soap,
        rest=rest,
        state=repo,
    )
    with pytest.raises(CsobBCHttpError):
        await mgr.download_new_files(DownloadFilter(file_types=[DownloadFileType.VYPIS]), tmp_path)


@pytest.mark.asyncio
async def test_download_metrics_populated(repo: SqliteStateRepository, tmp_path: Path):
    soap = MagicMock()
    rest = MagicMock()
    rest.download_to_file = AsyncMock()
    metrics = MetricsCollector()
    ts = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
    soap.get_download_file_list_v4 = AsyncMock(
        return_value=MagicMock(
            query_timestamp=ts,
            files=[
                DownloadFile(
                    filename="stmt.pdf",
                    type=DownloadFileType.VYPIS,
                    format="PDF",
                    creation_date_time=datetime(2025, 1, 14, 9, 0, 0, tzinfo=UTC),
                    size=1024,
                    status=DownloadFileStatus.D,
                    url="https://example.com/stmt.pdf",
                    upload_file_hash=None,
                )
            ],
        )
    )
    mgr = DownloadManager(
        contract_number="123456",
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        cert_fingerprint="fp",
        environment="production",
        soap=soap,
        rest=rest,
        state=repo,
        metrics=metrics,
    )
    await mgr.download_new_files(DownloadFilter(file_types=[DownloadFileType.VYPIS]), tmp_path)
    assert metrics.counter_value("download_soap_calls") == 1
    assert metrics.counter_value("download_success") == 1
    assert metrics.gauge_value("download_file_count") == 1.0
