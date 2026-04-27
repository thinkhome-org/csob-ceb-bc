from datetime import UTC, datetime
from pathlib import Path

import pytest

from csob_ceb_bc.state.sqlite_repo import SqliteStateRepository


@pytest.fixture
def repo(tmp_path: Path):
    db_path = tmp_path / "state.db"
    return SqliteStateRepository(f"sqlite:///{db_path}")


def test_get_set_profile_cursor(repo: SqliteStateRepository):
    key = "prod:123456:VYPIS"
    assert repo.get_profile_cursor(key) is None
    ts = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
    repo.set_profile_cursor(key, ts)
    assert repo.get_profile_cursor(key) == ts


def test_create_upload_attempt(repo: SqliteStateRepository):
    repo.create_upload_attempt(
        attempt_id="a1",
        filename="pay.xml",
        file_hash="abc123" * 10 + "ab",
        size=1024,
        file_format="XML SEPA",
        mode="AllOrNothing",
    )
    row = repo.get_upload_attempt("a1")
    assert row is not None
    assert row["filename"] == "pay.xml"
    assert row["status"] == "started"


def test_save_new_file_id(repo: SqliteStateRepository):
    repo.create_upload_attempt(
        attempt_id="a2",
        filename="pay.xml",
        file_hash="abc123" * 10 + "ab",
        size=1024,
        file_format="XML SEPA",
        mode="AllOrNothing",
    )
    repo.save_upload_new_file_id("a2", "NFID-123")
    row = repo.get_upload_attempt("a2")
    assert row["new_file_id"] == "NFID-123"


def test_idempotency_check(repo: SqliteStateRepository):
    h = "abc123" * 10 + "ab"
    repo.create_upload_attempt(
        attempt_id="a3",
        filename="pay.xml",
        file_hash=h,
        size=1,
        file_format="XML SEPA",
        mode="AllOrNothing",
    )
    repo.mark_idempotency_key(h, "a3")
    assert repo.get_attempt_id_by_hash(h) == "a3"
