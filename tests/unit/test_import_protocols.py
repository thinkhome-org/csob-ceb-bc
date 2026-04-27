from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from csob_ceb_bc.import_protocols.manager import ImportProtocolManager
from csob_ceb_bc.models import DownloadFile, DownloadFileStatus, DownloadFileType
from csob_ceb_bc.state.sqlite_repo import SqliteStateRepository


@pytest.fixture
def repo(tmp_path: Path):
    return SqliteStateRepository(f"sqlite:///{tmp_path}/state.db")


def test_poll_import_protocols_pairs_by_hash(repo: SqliteStateRepository, tmp_path: Path):
    soap = MagicMock()
    rest = MagicMock()
    sha = "a" * 64
    soap.get_download_file_list_v4.return_value = MagicMock(
        query_timestamp=datetime.now(UTC),
        files=[
            DownloadFile(
                filename="prot.xml",
                type=DownloadFileType.IMPPROT,
                format="XML",
                creation_date_time=datetime.now(UTC),
                size=512,
                status=DownloadFileStatus.D,
                url="https://example.com/prot",
                upload_file_hash=sha,
            )
        ],
    )
    mgr = ImportProtocolManager(
        client_app_guid="guid",
        soap=soap,
        rest=rest,
        state=repo,
    )
    repo.create_import_protocol(
        new_file_id="NFID-1",
        upload_hash=sha,
        filename="pay.xml",
        client_app_guid="guid",
    )
    mgr.poll_import_protocols(tmp_path)
    rest.download_to_file.assert_called_once_with("https://example.com/prot", tmp_path / "prot.xml")
