from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from csob_ceb_bc.models import UploadFinishStatus
from csob_ceb_bc.state.sqlite_repo import SqliteStateRepository
from csob_ceb_bc.uploads.manager import UploadManager


@pytest.fixture
def repo(tmp_path: Path):
    return SqliteStateRepository(f"sqlite:///{tmp_path}/state.db")


@pytest.mark.asyncio
async def test_resume_pending_finishes_upload(repo: SqliteStateRepository, tmp_path: Path):
    # Simulate a crash after REST upload but before finish
    repo.create_upload_attempt(
        attempt_id="a1",
        filename="pay.xml",
        file_hash="a" * 64,
        size=100,
        file_format="XML SEPA",
        mode="AllOrNothing",
    )
    repo.save_upload_new_file_id("a1", "NFID-1")

    soap = MagicMock()
    soap.finish_upload_file_list_v2 = AsyncMock(
        return_value=[
            MagicMock(
                filename="pay.xml",
                hash="a" * 64,
                status=UploadFinishStatus.I,
                ticket_id="T1",
            )
        ]
    )

    mgr = UploadManager(
        contract_number="123456",
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        soap=soap,
        rest=MagicMock(),
        state=repo,
    )
    results = await mgr.resume_pending()
    assert len(results) == 1
    assert results[0].status == UploadFinishStatus.I

    # Verify state updated
    row = repo.get_upload_attempt("a1")
    assert row is not None
    assert "finish_I" in row["status"]
