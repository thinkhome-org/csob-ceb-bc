"""Tests for BusinessConnectorClient metrics wiring."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from csob_ceb_bc.client import BusinessConnectorClient
from csob_ceb_bc.config import CertificateConfig, ConnectorConfig, Environment
from csob_ceb_bc.metrics import MetricsCollector

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


@patch("csob_ceb_bc.client.AsyncSoapGateway")
@patch("csob_ceb_bc.client.AsyncRestTransferClient")
@patch("csob_ceb_bc.client.SqliteStateRepository")
def test_metrics_snapshot_returns_data(mock_state, mock_rest, mock_soap):
    config = _config()
    cert_store = MagicMock()
    cert_store.cert_path.read_bytes.return_value = b"cert"
    metrics = MetricsCollector()
    metrics.inc("download_soap_calls", 5)

    client = BusinessConnectorClient(
        config=config,
        soap=mock_soap,
        rest=mock_rest,
        state=mock_state,
        cert_store=cert_store,
        metrics=metrics,
    )

    snap = client.metrics_snapshot()
    assert snap["counters"]["download_soap_calls"] == 5


@patch("csob_ceb_bc.client.AsyncSoapGateway")
@patch("csob_ceb_bc.client.AsyncRestTransferClient")
@patch("csob_ceb_bc.client.SqliteStateRepository")
def test_default_metrics_collector(mock_state, mock_rest, mock_soap):
    config = _config()
    cert_store = MagicMock()
    cert_store.cert_path.read_bytes.return_value = b"cert"

    client = BusinessConnectorClient(
        config=config,
        soap=mock_soap,
        rest=mock_rest,
        state=mock_state,
        cert_store=cert_store,
    )

    assert client.metrics_snapshot() is not None
