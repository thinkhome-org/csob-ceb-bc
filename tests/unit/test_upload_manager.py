import hashlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from csob_ceb_bc.metrics import MetricsCollector
from csob_ceb_bc.models import (
    UploadFile,
    UploadFinishStatus,
    UploadMode,
    UploadStartStatus,
)
from csob_ceb_bc.state.sqlite_repo import SqliteStateRepository
from csob_ceb_bc.uploads.manager import UploadManager


@pytest.fixture
def repo(tmp_path: Path):
    return SqliteStateRepository(f"sqlite:///{tmp_path}/state.db")


def test_compute_sha256(tmp_path: Path):
    file_path = tmp_path / "test.txt"
    file_path.write_text("hello")
    expected = hashlib.sha256(b"hello").hexdigest()
    mgr = UploadManager(
        contract_number="123456",
        client_app_guid="guid",
        soap=MagicMock(),
        rest=MagicMock(),
        state=MagicMock(),
    )
    assert mgr.compute_sha256(file_path) == expected


def test_upload_payment_batch_rejected_at_start(repo: SqliteStateRepository, tmp_path: Path):
    file_path = tmp_path / "pay.xml"
    file_path.write_text("<payments/>")
    soap = MagicMock()
    rest = MagicMock()
    soap.start_upload_file_list_v3.return_value = [
        MagicMock(filename="pay.xml", status=UploadStartStatus.R, url=None, ticket_id="T1")
    ]
    mgr = UploadManager(
        contract_number="123456",
        client_app_guid="guid",
        soap=soap,
        rest=rest,
        state=repo,
    )
    result = mgr.upload_payment_batch(
        file=file_path,
        metadata=UploadFile(filename="pay.xml", format="XML SEPA", mode=UploadMode.AllOrNothing),
    )
    assert result is None
    rest.upload_multipart.assert_not_called()


def test_upload_payment_batch_success_flow(repo: SqliteStateRepository, tmp_path: Path):
    file_path = tmp_path / "pay.xml"
    file_path.write_text("<payments/>")
    sha = hashlib.sha256(b"<payments/>").hexdigest()

    soap = MagicMock()
    rest = MagicMock()
    soap.start_upload_file_list_v3.return_value = [
        MagicMock(filename="pay.xml", status=UploadStartStatus.U, url="https://up", ticket_id="T2")
    ]
    from csob_ceb_bc.models import RestUploadResult

    rest.upload_multipart.return_value = RestUploadResult(
        status="201", ext_file_url="", new_file_id="NFID-1"
    )
    soap.finish_upload_file_list_v2.return_value = [
        MagicMock(filename="pay.xml", hash=sha, status=UploadFinishStatus.I, ticket_id="T3")
    ]

    mgr = UploadManager(
        contract_number="123456",
        client_app_guid="guid",
        soap=soap,
        rest=rest,
        state=repo,
    )
    result = mgr.upload_payment_batch(
        file=file_path,
        metadata=UploadFile(filename="pay.xml", format="XML SEPA", mode=UploadMode.AllOrNothing),
    )
    assert result is not None
    assert result.status == UploadFinishStatus.I


def test_upload_idempotent_skip(repo: SqliteStateRepository, tmp_path: Path):
    file_path = tmp_path / "pay.xml"
    file_path.write_text("<payments/>")
    sha = hashlib.sha256(b"<payments/>").hexdigest()
    repo.create_upload_attempt(
        attempt_id="a1", filename="pay.xml", file_hash=sha, size=12, file_format="XML SEPA", mode="AllOrNothing"
    )
    repo.mark_idempotency_key(sha, "a1")

    soap = MagicMock()
    rest = MagicMock()
    metrics = MetricsCollector()

    mgr = UploadManager(
        contract_number="123456",
        client_app_guid="guid",
        soap=soap,
        rest=rest,
        state=repo,
        metrics=metrics,
    )
    result = mgr.upload_payment_batch(
        file=file_path,
        metadata=UploadFile(filename="pay.xml", format="XML SEPA", mode=UploadMode.AllOrNothing),
    )
    assert result is None
    soap.start_upload_file_list_v3.assert_not_called()
    assert metrics.counter_value("upload_idempotent_skips") == 1


def test_upload_empty_start_results(repo: SqliteStateRepository, tmp_path: Path):
    file_path = tmp_path / "pay.xml"
    file_path.write_text("<payments/>")
    soap = MagicMock()
    soap.start_upload_file_list_v3.return_value = []
    rest = MagicMock()

    mgr = UploadManager(
        contract_number="123456",
        client_app_guid="guid",
        soap=soap,
        rest=rest,
        state=repo,
    )
    result = mgr.upload_payment_batch(
        file=file_path,
        metadata=UploadFile(filename="pay.xml", format="XML SEPA", mode=UploadMode.AllOrNothing),
    )
    assert result is None


def test_upload_start_u_without_url(repo: SqliteStateRepository, tmp_path: Path):
    file_path = tmp_path / "pay.xml"
    file_path.write_text("<payments/>")
    soap = MagicMock()
    soap.start_upload_file_list_v3.return_value = [
        MagicMock(filename="pay.xml", status=UploadStartStatus.U, url=None, ticket_id="T1")
    ]
    rest = MagicMock()

    mgr = UploadManager(
        contract_number="123456",
        client_app_guid="guid",
        soap=soap,
        rest=rest,
        state=repo,
    )
    result = mgr.upload_payment_batch(
        file=file_path,
        metadata=UploadFile(filename="pay.xml", format="XML SEPA", mode=UploadMode.AllOrNothing),
    )
    assert result is None


def test_upload_rejected_with_metrics(repo: SqliteStateRepository, tmp_path: Path):
    file_path = tmp_path / "pay.xml"
    file_path.write_text("<payments/>")
    soap = MagicMock()
    soap.start_upload_file_list_v3.return_value = [
        MagicMock(filename="pay.xml", status=UploadStartStatus.R, url=None, ticket_id="T1")
    ]
    metrics = MetricsCollector()

    mgr = UploadManager(
        contract_number="123456",
        client_app_guid="guid",
        soap=soap,
        rest=MagicMock(),
        state=repo,
        metrics=metrics,
    )
    result = mgr.upload_payment_batch(
        file=file_path,
        metadata=UploadFile(filename="pay.xml", format="XML SEPA", mode=UploadMode.AllOrNothing),
    )
    assert result is None
    assert metrics.counter_value("upload_rejected") == 1


def test_upload_finish_rejected_with_metrics(repo: SqliteStateRepository, tmp_path: Path):
    file_path = tmp_path / "pay.xml"
    file_path.write_text("<payments/>")
    sha = hashlib.sha256(b"<payments/>").hexdigest()

    soap = MagicMock()
    rest = MagicMock()
    soap.start_upload_file_list_v3.return_value = [
        MagicMock(filename="pay.xml", status=UploadStartStatus.U, url="https://up", ticket_id="T2")
    ]
    from csob_ceb_bc.models import RestUploadResult

    rest.upload_multipart.return_value = RestUploadResult(
        status="201", ext_file_url="", new_file_id="NFID-1"
    )
    soap.finish_upload_file_list_v2.return_value = [
        MagicMock(filename="pay.xml", hash=sha, status=UploadFinishStatus.R, ticket_id="T3")
    ]

    metrics = MetricsCollector()
    mgr = UploadManager(
        contract_number="123456",
        client_app_guid="guid",
        soap=soap,
        rest=rest,
        state=repo,
        metrics=metrics,
    )
    result = mgr.upload_payment_batch(
        file=file_path,
        metadata=UploadFile(filename="pay.xml", format="XML SEPA", mode=UploadMode.AllOrNothing),
    )
    assert result is not None
    assert result.status == UploadFinishStatus.R
    assert metrics.counter_value("upload_finish_rejected") == 1


def test_resume_pending_with_metrics(repo: SqliteStateRepository, tmp_path: Path):
    repo.create_upload_attempt(
        attempt_id="a1",
        filename="pay.xml",
        file_hash="abc",
        size=1,
        file_format="XML SEPA",
        mode="AllOrNothing",
    )
    repo.save_upload_new_file_id("a1", "NFID-1")

    soap = MagicMock()
    soap.finish_upload_file_list_v2.return_value = [
        MagicMock(filename="pay.xml", hash="abc", status=UploadFinishStatus.I, ticket_id="T2")
    ]
    metrics = MetricsCollector()

    mgr = UploadManager(
        contract_number="123456",
        client_app_guid="guid",
        soap=soap,
        rest=MagicMock(),
        state=repo,
        metrics=metrics,
    )
    results = mgr.resume_pending()
    assert len(results) == 1
    assert metrics.counter_value("upload_resume_success") == 1
    assert metrics.gauge_value("upload_pending_count") == 1.0
