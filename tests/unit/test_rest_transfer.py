from pathlib import Path

import httpx
import pytest
import respx

from csob_ceb_bc.certificates.store import CertificateStore
from csob_ceb_bc.config import CertificateConfig
from csob_ceb_bc.errors import CsobBCHttpError
from csob_ceb_bc.rest.transfer import RestTransferClient

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _store() -> CertificateStore:
    return CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "test.key",
        )
    )


@respx.mock
def test_download_to_file_success(tmp_path: Path):
    route = respx.get("https://example.com/file").mock(
        return_value=httpx.Response(200, content=b"hello")
    )
    client = RestTransferClient(cert_store=_store())
    target = tmp_path / "out.bin"
    result = client.download_to_file("https://example.com/file", target)
    assert result.http_status == 200
    assert target.read_bytes() == b"hello"
    assert route.called


@respx.mock
def test_download_to_file_404_permanent():
    respx.get("https://example.com/file").mock(return_value=httpx.Response(404))
    client = RestTransferClient(cert_store=_store())
    with pytest.raises(CsobBCHttpError) as exc_info:
        client.download_to_file("https://example.com/file", Path("/dev/null"))
    assert exc_info.value.permanent is True


@respx.mock
def test_upload_multipart_success():
    respx.post("https://example.com/upload").mock(
        return_value=httpx.Response(
            201,
            json={"Status": "201", "ExtFileUrl": "", "NewFileId": "NFID-abc"},
        )
    )
    client = RestTransferClient(cert_store=_store())
    file_path = FIXTURES / "certs" / "test.pem"
    result = client.upload_multipart("https://example.com/upload", file_path, "test.pem")
    assert result.status == "201"
    assert result.new_file_id == "NFID-abc"
