"""Async REST transfer client tests."""

from pathlib import Path
from unittest.mock import patch

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
    result = await client.upload_multipart("https://example.com/upload", file_path, "test.pem")
    assert result.status == "201"
    assert result.new_file_id == "NFID-abc"


@respx.mock
@pytest.mark.asyncio
async def test_async_upload_malformed_json():
    respx.post("https://example.com/upload").mock(return_value=httpx.Response(200, text="not-json"))
    client = AsyncRestTransferClient(cert_store=_store())
    file_path = FIXTURES / "certs" / "test.pem"
    with pytest.raises(CsobBCProtocolError) as exc_info:
        await client.upload_multipart("https://example.com/upload", file_path, "test.pem")
    assert "non-JSON" in str(exc_info.value)


@respx.mock
@pytest.mark.asyncio
async def test_async_upload_malformed_schema():
    respx.post("https://example.com/upload").mock(
        return_value=httpx.Response(200, json={"unexpected": "field"})
    )
    client = AsyncRestTransferClient(cert_store=_store())
    file_path = FIXTURES / "certs" / "test.pem"
    with pytest.raises(CsobBCProtocolError) as exc_info:
        await client.upload_multipart("https://example.com/upload", file_path, "test.pem")
    assert "schema" in str(exc_info.value).lower() or "JSON" in str(exc_info.value)


@respx.mock
@pytest.mark.asyncio
async def test_async_download_connection_timeout(tmp_path: Path):
    route = respx.get("https://example.com/file").mock(
        side_effect=httpx.ConnectTimeout("Connection timed out")
    )
    client = AsyncRestTransferClient(cert_store=_store())
    with pytest.raises(CsobBCHttpError) as exc_info:
        await client.download_to_file("https://example.com/file", tmp_path / "out.bin")
    assert exc_info.value.retryable is True
    assert route.called


@respx.mock
@pytest.mark.asyncio
async def test_async_download_read_timeout(tmp_path: Path):
    route = respx.get("https://example.com/file").mock(
        side_effect=httpx.ReadTimeout("Read timed out")
    )
    client = AsyncRestTransferClient(cert_store=_store())
    with pytest.raises(CsobBCHttpError) as exc_info:
        await client.download_to_file("https://example.com/file", tmp_path / "out.bin")
    assert exc_info.value.retryable is True
    assert route.called


@respx.mock
@pytest.mark.asyncio
async def test_async_upload_connection_error():
    route = respx.post("https://example.com/upload").mock(
        side_effect=httpx.ConnectError("No route to host")
    )
    client = AsyncRestTransferClient(cert_store=_store())
    file_path = FIXTURES / "certs" / "test.pem"
    with pytest.raises(httpx.ConnectError):
        await client.upload_multipart("https://example.com/upload", file_path, "test.pem")
    assert route.called


@respx.mock
@pytest.mark.asyncio
async def test_async_download_503_retryable():
    respx.get("https://example.com/file").mock(return_value=httpx.Response(503))
    client = AsyncRestTransferClient(cert_store=_store())
    with pytest.raises(CsobBCHttpError) as exc_info:
        await client.download_to_file("https://example.com/file", Path("/dev/null"))
    assert exc_info.value.retryable is True
    assert exc_info.value.permanent is False


@respx.mock
@pytest.mark.asyncio
async def test_async_upload_500_retryable():
    respx.post("https://example.com/upload").mock(return_value=httpx.Response(500))
    client = AsyncRestTransferClient(cert_store=_store())
    file_path = FIXTURES / "certs" / "test.pem"
    with pytest.raises(CsobBCHttpError) as exc_info:
        await client.upload_multipart("https://example.com/upload", file_path, "test.pem")
    assert exc_info.value.retryable is True


@respx.mock
@pytest.mark.asyncio
async def test_async_download_cleans_up_part_on_error(tmp_path: Path):
    route = respx.get("https://example.com/file").mock(
        return_value=httpx.Response(200, content=b"hello")
    )
    client = AsyncRestTransferClient(cert_store=_store())
    target = tmp_path / "out.bin"
    with (
        patch("pathlib.Path.rename", side_effect=PermissionError("denied")),
        pytest.raises(PermissionError),
    ):
        await client.download_to_file("https://example.com/file", target)
    assert not (tmp_path / "out.bin.part").exists()
    assert route.called


@respx.mock
@pytest.mark.asyncio
async def test_async_upload_429_retryable():
    respx.post("https://example.com/upload").mock(return_value=httpx.Response(429))
    client = AsyncRestTransferClient(cert_store=_store())
    file_path = FIXTURES / "certs" / "test.pem"
    with pytest.raises(CsobBCHttpError) as exc_info:
        await client.upload_multipart("https://example.com/upload", file_path, "test.pem")
    assert exc_info.value.retryable is True


@respx.mock
@pytest.mark.asyncio
async def test_async_upload_json_450_permanent():
    respx.post("https://example.com/upload").mock(
        return_value=httpx.Response(200, json={"Status": "450", "ExtFileUrl": "", "NewFileId": ""})
    )
    client = AsyncRestTransferClient(cert_store=_store())
    file_path = FIXTURES / "certs" / "test.pem"
    with pytest.raises(CsobBCHttpError) as exc_info:
        await client.upload_multipart("https://example.com/upload", file_path, "test.pem")
    assert exc_info.value.permanent is True


@respx.mock
@pytest.mark.asyncio
async def test_async_upload_json_455_retryable():
    respx.post("https://example.com/upload").mock(
        return_value=httpx.Response(200, json={"Status": "455", "ExtFileUrl": "", "NewFileId": ""})
    )
    client = AsyncRestTransferClient(cert_store=_store())
    file_path = FIXTURES / "certs" / "test.pem"
    with pytest.raises(CsobBCHttpError) as exc_info:
        await client.upload_multipart("https://example.com/upload", file_path, "test.pem")
    assert exc_info.value.retryable is True


@respx.mock
@pytest.mark.asyncio
async def test_async_upload_json_unexpected_status():
    respx.post("https://example.com/upload").mock(
        return_value=httpx.Response(200, json={"Status": "999", "ExtFileUrl": "", "NewFileId": ""})
    )
    client = AsyncRestTransferClient(cert_store=_store())
    file_path = FIXTURES / "certs" / "test.pem"
    with pytest.raises(CsobBCHttpError) as exc_info:
        await client.upload_multipart("https://example.com/upload", file_path, "test.pem")
    assert exc_info.value.permanent is False
    assert exc_info.value.retryable is False


@respx.mock
@pytest.mark.asyncio
async def test_async_upload_connection_timeout():
    route = respx.post("https://example.com/upload").mock(
        side_effect=httpx.ConnectTimeout("Connection timed out")
    )
    client = AsyncRestTransferClient(cert_store=_store())
    file_path = FIXTURES / "certs" / "test.pem"
    with pytest.raises(CsobBCHttpError) as exc_info:
        await client.upload_multipart("https://example.com/upload", file_path, "test.pem")
    assert exc_info.value.retryable is True
    assert route.called
