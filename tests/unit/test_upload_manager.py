import hashlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from csob_ceb_bc.uploads.manager import UploadManager
from csob_ceb_bc.models import UploadFile, UploadMode, UploadStartStatus, UploadFinishStatus
from csob_ceb_bc.state.sqlite_repo import SqliteStateRepository


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
