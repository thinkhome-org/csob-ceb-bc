"""Tests for BusinessConnectorClient high-level methods."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from csob_ceb_bc.client import BusinessConnectorClient
from csob_ceb_bc.config import CertificateConfig, ConnectorConfig, Environment
from csob_ceb_bc.models import DownloadBatchResult, DownloadFilter, UploadFile, UploadMode

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _config() -> ConnectorConfig:
    return ConnectorConfig(
        environment=Environment.DEMO,
        contract_number="123456",
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        certificate=CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "test.key",
        ),
        state_url="sqlite:///:memory:",
    )


@pytest.mark.asyncio
@patch("csob_ceb_bc.client.AsyncSoapGateway")
@patch("csob_ceb_bc.client.AsyncRestTransferClient")
@patch("csob_ceb_bc.client.SqliteStateRepository")
async def test_download_new_files_delegates(mock_state, mock_rest, mock_soap):
    config = _config()
    cert_store = MagicMock()
    cert_store.cert_path.read_bytes.return_value = b"cert"

    dm = MagicMock()
    dm.download_new_files = AsyncMock(return_value=DownloadBatchResult())

    client = BusinessConnectorClient(
        config=config,
        soap=mock_soap,
        rest=mock_rest,
        state=mock_state,
        cert_store=cert_store,
    )
    client._download_manager = dm

    result = await client.download_new_files(DownloadFilter(file_types=["VYPIS"]), Path("/tmp"))
    dm.download_new_files.assert_awaited_once()
    assert isinstance(result, DownloadBatchResult)


@pytest.mark.asyncio
@patch("csob_ceb_bc.client.AsyncSoapGateway")
@patch("csob_ceb_bc.client.AsyncRestTransferClient")
@patch("csob_ceb_bc.client.SqliteStateRepository")
async def test_poll_import_protocols_default_dir(mock_state, mock_rest, mock_soap):
    config = _config()
    cert_store = MagicMock()
    cert_store.cert_path.read_bytes.return_value = b"cert"

    ipm = MagicMock()
    ipm.poll_import_protocols = AsyncMock(return_value=DownloadBatchResult())

    client = BusinessConnectorClient(
        config=config,
        soap=mock_soap,
        rest=mock_rest,
        state=mock_state,
        cert_store=cert_store,
    )
    client._import_protocol_manager = ipm

    result = await client.poll_import_protocols()
    ipm.poll_import_protocols.assert_awaited_once_with(Path("."))
    assert isinstance(result, DownloadBatchResult)


@pytest.mark.asyncio
@patch("csob_ceb_bc.client.AsyncSoapGateway")
@patch("csob_ceb_bc.client.AsyncRestTransferClient")
@patch("csob_ceb_bc.client.SqliteStateRepository")
async def test_resume_pending_delegates(mock_state, mock_rest, mock_soap):
    config = _config()
    cert_store = MagicMock()
    cert_store.cert_path.read_bytes.return_value = b"cert"

    um = MagicMock()
    um.resume_pending = AsyncMock(return_value=[])

    client = BusinessConnectorClient(
        config=config,
        soap=mock_soap,
        rest=mock_rest,
        state=mock_state,
        cert_store=cert_store,
    )
    client._upload_manager = um

    await client.resume_pending()
    um.resume_pending.assert_awaited_once()


@pytest.mark.asyncio
@patch("csob_ceb_bc.client.AsyncSoapGateway")
@patch("csob_ceb_bc.client.AsyncRestTransferClient")
@patch("csob_ceb_bc.client.SqliteStateRepository")
async def test_upload_payment_batch_delegates(mock_state, mock_rest, mock_soap):
    config = _config()
    cert_store = MagicMock()
    cert_store.cert_path.read_bytes.return_value = b"cert"

    um = MagicMock()
    um.upload_payment_batch = AsyncMock(return_value=None)

    client = BusinessConnectorClient(
        config=config,
        soap=mock_soap,
        rest=mock_rest,
        state=mock_state,
        cert_store=cert_store,
    )
    client._upload_manager = um

    file_path = FIXTURES / "certs" / "test.pem"
    metadata = UploadFile(filename="test.xml", format="XML SEPA", mode=UploadMode.AllOrNothing)
    result = await client.upload_payment_batch(file_path, metadata)
    um.upload_payment_batch.assert_awaited_once()
    assert result is None
