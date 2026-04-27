"""Async REST transfer client tests."""

from pathlib import Path

import httpx
import pytest
import respx

from csob_ceb_bc.certificates.store import CertificateStore
from csob_ceb_bc.config import CertificateConfig
from csob_ceb_bc.errors import CsobBCHttpError, CsobBCProtocolError
from csob_ceb_bc.rest.async_transfer import AsyncRestTransferClient

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _store() -> CertificateStore:
    return CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "test.key",
        )
    )


@respx.mock
@pytest.mark.asyncio
async def test_async_download_to_file_success(tmp_path: Path):
    route = respx.get("https://example.com/file").mock(
        return_value=httpx.Response(200, content=b"hello")
    )
    client = AsyncRestTransferClient(cert_store=_store())
    target = tmp_path / "out.bin"
    result = await client.download_to_file("https://example.com/file", target)
    assert result.http_status == 200
    assert target.read_bytes() == b"hello"
    assert route.called


@respx.mock
@pytest.mark.asyncio
async def test_async_download_404_permanent():
    respx.get("https://example.com/file").mock(return_value=httpx.Response(404))
    client = AsyncRestTransferClient(cert_store=_store())
    with pytest.raises(CsobBCHttpError) as exc_info:
        await client.download_to_file("https://example.com/file", Path("/dev/null"))
    assert exc_info.value.permanent is True


@respx.mock
@pytest.mark.asyncio
async def test_async_upload_multipart_success():
    respx.post("https://example.com/upload").mock(
        return_value=httpx.Response(
            201,
            json={"Status": "201", "ExtFileUrl": "", "NewFileId": "NFID-abc"},
        )
    )
    client = AsyncRestTransferClient(cert_store=_store())
    file_path = FIXTURES / "certs" / "test.pem"
    result = await client.upload_multipart(
        "https://example.com/upload", file_path, "test.pem"
    )
    assert result.status == "201"
    assert result.new_file_id == "NFID-abc"


@respx.mock
@pytest.mark.asyncio
async def test_async_upload_malformed_json():
    respx.post("https://example.com/upload").mock(
        return_value=httpx.Response(200, text="not-json")
    )
    client = AsyncRestTransferClient(cert_store=_store())
    file_path = FIXTURES / "certs" / "test.pem"
    with pytest.raises(CsobBCProtocolError) as exc_info:
        await client.upload_multipart(
            "https://example.com/upload", file_path, "test.pem"
        )
    assert "non-JSON" in str(exc_info.value)
