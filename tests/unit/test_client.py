from pathlib import Path
from unittest.mock import MagicMock, patch

from csob_ceb_bc.client import BusinessConnectorClient
from csob_ceb_bc.config import CertificateConfig, ConnectorConfig, Environment
from csob_ceb_bc.models import DownloadFilter


def _config() -> ConnectorConfig:
    return ConnectorConfig(
        environment=Environment.DEMO,
        contract_number="123456",
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        certificate=CertificateConfig(
            cert_file=Path("/dev/null"),
            key_file=Path("/dev/null"),
        ),
    )


@patch("csob_ceb_bc.client.SoapGateway")
@patch("csob_ceb_bc.client.RestTransferClient")
@patch("csob_ceb_bc.client.SqliteStateRepository")
@patch("csob_ceb_bc.client.CertificateStore")
def test_from_config_creates_client(mock_cert, mock_state, mock_rest, mock_soap):
    mock_cert_instance = MagicMock()
    mock_cert_instance.cert_path.read_bytes.return_value = b"cert"
    mock_cert.return_value = mock_cert_instance
    client = BusinessConnectorClient.from_config(_config())
    assert client is not None


@patch("csob_ceb_bc.client.SoapGateway")
@patch("csob_ceb_bc.client.RestTransferClient")
@patch("csob_ceb_bc.client.SqliteStateRepository")
@patch("csob_ceb_bc.client.CertificateStore")
def test_list_available_files_delegates(mock_cert, mock_state, mock_rest, mock_soap):
    mock_cert_instance = MagicMock()
    mock_cert_instance.cert_path.read_bytes.return_value = b"cert"
    mock_cert.return_value = mock_cert_instance
    client = BusinessConnectorClient.from_config(_config())
    dm = MagicMock()
    client._download_manager = dm
    dm.list_available_files.return_value = []
    result = client.list_available_files(DownloadFilter())
    assert result == []
    dm.list_available_files.assert_called_once()
