"""Tests for BusinessConnectorClient high-level methods."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from csob_ceb_bc.client import BusinessConnectorClient
from csob_ceb_bc.config import CertificateConfig, ConnectorConfig, Environment
from csob_ceb_bc.models import DownloadFilter, UploadFile, UploadMode

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _config() -> ConnectorConfig:
    return ConnectorConfig(
        environment=Environment.DEMO,
        contract_number="123456",
        client_app_guid="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        certificate=CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "test.key",
        ),
        state_url="sqlite:///:memory:",
    )


@patch("csob_ceb_bc.client.SoapGateway")
@patch("csob_ceb_bc.client.RestTransferClient")
@patch("csob_ceb_bc.client.SqliteStateRepository")
def test_download_new_files_delegates(mock_state, mock_rest, mock_soap):
    config = _config()
    cert_store = MagicMock()
    cert_store.cert_path.read_bytes.return_value = b"cert"

    dm = MagicMock()
    dm.download_new_files.return_value = []

    client = BusinessConnectorClient(
        config=config,
        soap=mock_soap,
        rest=mock_rest,
        state=mock_state,
        cert_store=cert_store,
    )
    client._download_manager = dm

    result = client.download_new_files(DownloadFilter(file_types=["VYPIS"]), Path("/tmp"))
    dm.download_new_files.assert_called_once()
    assert result == []


@patch("csob_ceb_bc.client.SoapGateway")
@patch("csob_ceb_bc.client.RestTransferClient")
@patch("csob_ceb_bc.client.SqliteStateRepository")
def test_poll_import_protocols_default_dir(mock_state, mock_rest, mock_soap):
    config = _config()
    cert_store = MagicMock()
    cert_store.cert_path.read_bytes.return_value = b"cert"

    ipm = MagicMock()
    ipm.poll_import_protocols.return_value = []

    client = BusinessConnectorClient(
        config=config,
        soap=mock_soap,
        rest=mock_rest,
        state=mock_state,
        cert_store=cert_store,
    )
    client._import_protocol_manager = ipm

    result = client.poll_import_protocols()
    ipm.poll_import_protocols.assert_called_once_with(Path("."))
    assert result == []


@patch("csob_ceb_bc.client.SoapGateway")
@patch("csob_ceb_bc.client.RestTransferClient")
@patch("csob_ceb_bc.client.SqliteStateRepository")
def test_resume_pending_delegates(mock_state, mock_rest, mock_soap):
    config = _config()
    cert_store = MagicMock()
    cert_store.cert_path.read_bytes.return_value = b"cert"

    um = MagicMock()
    um.resume_pending.return_value = []

    client = BusinessConnectorClient(
        config=config,
        soap=mock_soap,
        rest=mock_rest,
        state=mock_state,
        cert_store=cert_store,
    )
    client._upload_manager = um

    client.resume_pending()
    um.resume_pending.assert_called_once()


@patch("csob_ceb_bc.client.SoapGateway")
@patch("csob_ceb_bc.client.RestTransferClient")
@patch("csob_ceb_bc.client.SqliteStateRepository")
def test_upload_payment_batch_delegates(mock_state, mock_rest, mock_soap):
    config = _config()
    cert_store = MagicMock()
    cert_store.cert_path.read_bytes.return_value = b"cert"

    um = MagicMock()
    um.upload_payment_batch.return_value = None

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
    result = client.upload_payment_batch(file_path, metadata)
    um.upload_payment_batch.assert_called_once()
    assert result is None
