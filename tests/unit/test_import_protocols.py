"""Tests for ImportProtocolManager including metrics branches."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from csob_ceb_bc.import_protocols.manager import ImportProtocolManager
from csob_ceb_bc.metrics import MetricsCollector
from csob_ceb_bc.models import DownloadFile, DownloadFileStatus, DownloadFileType
from csob_ceb_bc.soap.gateway import DownloadListResult


@pytest.mark.asyncio
async def test_poll_import_protocols_with_metrics(tmp_path: Path):
    soap = MagicMock()
    soap.get_download_file_list_v4 = AsyncMock(
        return_value=DownloadListResult(
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
    )
    rest = MagicMock()
    rest.download_to_file = AsyncMock()
    metrics = MetricsCollector()
    state = MagicMock()
    state.get_profile_cursor.return_value = None
    state.get_attempt_id_by_hash.return_value = "a1"

    mgr = ImportProtocolManager(
        contract_number="123456",
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        environment="demo",
        soap=soap,
        rest=rest,
        state=state,
        metrics=metrics,
    )
    result = await mgr.poll_import_protocols(tmp_path)
    assert len(result) == 1
    assert metrics.counter_value("import_protocol_soap_calls") == 1
    assert metrics.counter_value("import_protocol_download_success") == 1
    assert metrics.gauge_value("import_protocol_file_count") == 1.0


@pytest.mark.asyncio
async def test_poll_import_protocols_skips_non_downloadable(tmp_path: Path):
    soap = MagicMock()
    soap.get_download_file_list_v4 = AsyncMock(
        return_value=DownloadListResult(
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
    )
    rest = MagicMock()
    rest.download_to_file = AsyncMock()
    state = MagicMock()
    state.get_profile_cursor.return_value = None

    mgr = ImportProtocolManager(
        contract_number="123456",
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        environment="demo",
        soap=soap,
        rest=rest,
        state=state,
    )
    result = await mgr.poll_import_protocols(tmp_path)
    assert len(result) == 0
    rest.download_to_file.assert_not_awaited()


@pytest.mark.asyncio
async def test_poll_import_protocols_downloads_unknown_hash(tmp_path: Path):
    """IMPPROT with UploadFileHash must be downloaded even without local idempotency key."""
    soap = MagicMock()
    soap.get_download_file_list_v4 = AsyncMock(
        return_value=DownloadListResult(
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
                    upload_file_hash="unknown-hash",
                )
            ],
        )
    )
    rest = MagicMock()
    rest.download_to_file = AsyncMock()
    state = MagicMock()
    state.get_profile_cursor.return_value = None
    state.get_attempt_id_by_hash.return_value = None

    mgr = ImportProtocolManager(
        contract_number="123456",
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        environment="demo",
        soap=soap,
        rest=rest,
        state=state,
    )
    result = await mgr.poll_import_protocols(tmp_path)
    assert len(result) == 1
    rest.download_to_file.assert_awaited_once()


@pytest.mark.asyncio
async def test_poll_import_protocols_retryable_rest_error_raised(tmp_path: Path):
    from csob_ceb_bc.errors import CsobBCHttpError

    soap = MagicMock()
    soap.get_download_file_list_v4 = AsyncMock(
        return_value=DownloadListResult(
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
    )
    rest = MagicMock()
    rest.download_to_file = AsyncMock(
        side_effect=CsobBCHttpError(
            "Server Error", operation="download", permanent=False, retryable=True
        )
    )
    state = MagicMock()
    state.get_profile_cursor.return_value = None
    state.get_attempt_id_by_hash.return_value = "a1"

    mgr = ImportProtocolManager(
        contract_number="123456",
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        environment="demo",
        soap=soap,
        rest=rest,
        state=state,
    )
    with pytest.raises(CsobBCHttpError):
        await mgr.poll_import_protocols(tmp_path)
