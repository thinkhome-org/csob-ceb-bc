"""Tests for AsyncImportProtocolManager."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from csob_ceb_bc.import_protocols.async_manager import AsyncImportProtocolManager
from csob_ceb_bc.metrics import MetricsCollector
from csob_ceb_bc.models import DownloadFile, DownloadFileStatus, DownloadFileType


@pytest_asyncio.fixture
async def mgr(tmp_path: Path):
    state = MagicMock()
    state.get_profile_cursor.return_value = None
    state.get_attempt_id_by_hash.return_value = "a1"

    soap = MagicMock()
    soap.get_download_file_list_v4.return_value = MagicMock(
        query_timestamp=datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
        files=[
            DownloadFile(
                filename="prot.xml",
                type=DownloadFileType.IMPPROT,
                format="XML",
                creation_date_time=datetime(2025, 1, 14, 9, 0, 0, tzinfo=UTC),
                size=512,
                status=DownloadFileStatus.D,
                url="https://example.com/prot.xml",
                upload_file_hash="abc123",
            )
        ],
    )
    async_rest = AsyncMock()
    metrics = MetricsCollector()

    manager = AsyncImportProtocolManager(
        contract_number="123456",
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        environment="demo",
        soap=soap,
        async_rest=async_rest,
        state=state,
        metrics=metrics,
    )
    return manager


@pytest.mark.asyncio
async def test_async_poll_import_protocols(mgr: AsyncImportProtocolManager, tmp_path: Path):
    result = await mgr.poll_import_protocols(tmp_path)
    assert len(result.downloaded) == 1
    assert result.cursor_advanced is True
    mgr._async_rest.download_to_file.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_poll_skips_unresolved(mgr: AsyncImportProtocolManager, tmp_path: Path):
    mgr._soap.get_download_file_list_v4.return_value = MagicMock(
        query_timestamp=datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
        files=[
            DownloadFile(
                filename="prot.xml",
                type=DownloadFileType.IMPPROT,
                format="XML",
                creation_date_time=datetime(2025, 1, 14, 9, 0, 0, tzinfo=UTC),
                size=512,
                status=DownloadFileStatus.R,
                url=None,
                upload_file_hash=None,
            )
        ],
    )
    result = await mgr.poll_import_protocols(tmp_path)
    assert len(result.downloaded) == 0
    assert result.has_pending_files is True
    assert result.cursor_advanced is False
    mgr._async_rest.download_to_file.assert_not_awaited()
