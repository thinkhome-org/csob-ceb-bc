"""Tests for ImportProtocolManager including metrics branches."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from csob_ceb_bc.import_protocols.manager import ImportProtocolManager
from csob_ceb_bc.metrics import MetricsCollector
from csob_ceb_bc.models import DownloadFile, DownloadFileStatus, DownloadFileType
from csob_ceb_bc.soap.gateway import DownloadListResult


def test_poll_import_protocols_with_metrics():
    soap = MagicMock()
    soap.get_download_file_list_v4.return_value = DownloadListResult(
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
    rest = MagicMock()
    metrics = MetricsCollector()

    mgr = ImportProtocolManager(
        contract_number="123456",
        client_app_guid="guid",
        environment="demo",
        soap=soap,
        rest=rest,
        state=MagicMock(),
        metrics=metrics,
    )
    result = mgr.poll_import_protocols(Path("/tmp/protocols"))
    assert len(result) == 1
    assert metrics.counter_value("import_protocol_soap_calls") == 1
    assert metrics.counter_value("import_protocol_download_success") == 1
    assert metrics.gauge_value("import_protocol_file_count") == 1.0


def test_poll_import_protocols_skips_non_downloadable():
    soap = MagicMock()
    soap.get_download_file_list_v4.return_value = DownloadListResult(
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
    rest = MagicMock()
    metrics = MetricsCollector()

    mgr = ImportProtocolManager(
        contract_number="123456",
        client_app_guid="guid",
        environment="demo",
        soap=soap,
        rest=rest,
        state=MagicMock(),
        metrics=metrics,
    )
    result = mgr.poll_import_protocols(Path("/tmp/protocols"))
    assert len(result) == 0
    rest.download_to_file.assert_not_called()


def test_poll_import_protocols_skips_no_hash():
    soap = MagicMock()
    soap.get_download_file_list_v4.return_value = DownloadListResult(
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
                upload_file_hash=None,
            )
        ],
    )
    rest = MagicMock()

    mgr = ImportProtocolManager(
        contract_number="123456",
        client_app_guid="guid",
        environment="demo",
        soap=soap,
        rest=rest,
        state=MagicMock(),
    )
    result = mgr.poll_import_protocols(Path("/tmp/protocols"))
    assert len(result) == 0
    rest.download_to_file.assert_not_called()


def test_poll_import_protocols_no_metrics():
    soap = MagicMock()
    soap.get_download_file_list_v4.return_value = DownloadListResult(
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
    rest = MagicMock()

    mgr = ImportProtocolManager(
        contract_number="123456",
        client_app_guid="guid",
        environment="demo",
        soap=soap,
        rest=rest,
        state=MagicMock(),
    )
    result = mgr.poll_import_protocols(Path("/tmp/protocols"))
    assert len(result) == 1
    rest.download_to_file.assert_called_once()


def test_poll_import_protocols_skips_f_status():
    import tempfile
    from pathlib import Path

    from csob_ceb_bc.state.sqlite_repo import SqliteStateRepository

    with tempfile.TemporaryDirectory() as td:
        state = SqliteStateRepository(f"sqlite:///{td}/state.db")
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
                    status=DownloadFileStatus.F,
                    url=None,
                    upload_file_hash=None,
                )
            ],
        )
        rest = MagicMock()
        mgr = ImportProtocolManager(
            contract_number="123456",
            client_app_guid="guid",
            environment="demo",
            soap=soap,
            rest=rest,
            state=state,
        )
        result = mgr.poll_import_protocols(Path(td))
        assert len(result) == 0


def test_poll_import_protocols_skips_unknown_hash():
    import tempfile
    from pathlib import Path

    from csob_ceb_bc.state.sqlite_repo import SqliteStateRepository

    with tempfile.TemporaryDirectory() as td:
        state = SqliteStateRepository(f"sqlite:///{td}/state.db")
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
                    upload_file_hash="unknown-hash",
                )
            ],
        )
        rest = MagicMock()
        mgr = ImportProtocolManager(
            contract_number="123456",
            client_app_guid="guid",
            environment="demo",
            soap=soap,
            rest=rest,
            state=state,
        )
        result = mgr.poll_import_protocols(Path(td))
        assert len(result) == 0


def test_poll_import_protocols_permanent_rest_error_skipped():
    import tempfile
    from pathlib import Path

    from csob_ceb_bc.errors import CsobBCHttpError
    from csob_ceb_bc.state.sqlite_repo import SqliteStateRepository

    with tempfile.TemporaryDirectory() as td:
        state = SqliteStateRepository(f"sqlite:///{td}/state.db")
        state.create_upload_attempt(
            attempt_id="a1",
            filename="pay.xml",
            file_hash="abc123",
            size=1,
            file_format="XML SEPA",
            mode="AllOrNothing",
        )
        state.mark_idempotency_key("abc123", "a1")
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
        rest = MagicMock()
        rest.download_to_file.side_effect = CsobBCHttpError(
            "Not Found", operation="download", permanent=True, retryable=False
        )
        mgr = ImportProtocolManager(
            contract_number="123456",
            client_app_guid="guid",
            environment="demo",
            soap=soap,
            rest=rest,
            state=state,
        )
        result = mgr.poll_import_protocols(Path(td))
        assert len(result) == 0


def test_poll_import_protocols_retryable_rest_error_raised():
    import tempfile
    from pathlib import Path

    from csob_ceb_bc.errors import CsobBCHttpError
    from csob_ceb_bc.state.sqlite_repo import SqliteStateRepository

    with tempfile.TemporaryDirectory() as td:
        state = SqliteStateRepository(f"sqlite:///{td}/state.db")
        state.create_upload_attempt(
            attempt_id="a1",
            filename="pay.xml",
            file_hash="abc123",
            size=1,
            file_format="XML SEPA",
            mode="AllOrNothing",
        )
        state.mark_idempotency_key("abc123", "a1")
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
        rest = MagicMock()
        rest.download_to_file.side_effect = CsobBCHttpError(
            "Server Error", operation="download", permanent=False, retryable=True
        )
        mgr = ImportProtocolManager(
            contract_number="123456",
            client_app_guid="guid",
            environment="demo",
            soap=soap,
            rest=rest,
            state=state,
        )
        with pytest.raises(CsobBCHttpError):
            mgr.poll_import_protocols(Path(td))
