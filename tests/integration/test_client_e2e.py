"""Lightweight integration test using mocked SOAP/REST."""
from pathlib import Path
from unittest.mock import MagicMock, patch

from csob_ceb_bc.client import BusinessConnectorClient
from csob_ceb_bc.config import ConnectorConfig, CertificateConfig, Environment
from csob_ceb_bc.models import DownloadFilter, UploadFile, UploadMode


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


@patch("csob_ceb_bc.client.CertificateStore")
@patch("csob_ceb_bc.client.SqliteStateRepository")
@patch("csob_ceb_bc.client.RestTransferClient")
@patch("csob_ceb_bc.client.SoapGateway")
def test_full_download_upload_flow(mock_soap, mock_rest, mock_state, mock_cert, tmp_path: Path):
    # Arrange mocks
    cert_store = MagicMock()
    cert_store.cert_path.read_bytes.return_value = b"cert"
    mock_cert.return_value = cert_store

    state = MagicMock()
    state.get_attempt_id_by_hash.return_value = None
    mock_state.return_value = state

    soap = MagicMock()
    mock_soap.return_value = soap

    rest = MagicMock()
    mock_rest.return_value = rest

    client = BusinessConnectorClient.from_config(_config())

    # Act & Assert: list files
    soap.get_download_file_list_v4.return_value = MagicMock(
        query_timestamp=None, files=[]
    )
    files = client.list_available_files(DownloadFilter())
    assert files == []

    # Act & Assert: upload
    from csob_ceb_bc.models import UploadStartStatus, UploadFinishStatus, RestUploadResult
    soap.start_upload_file_list_v3.return_value = [
        MagicMock(filename="pay.xml", status=UploadStartStatus.U, url="https://up", ticket_id="T1")
    ]
    rest.upload_multipart.return_value = RestUploadResult(
        status="201", ext_file_url="", new_file_id="NFID-1"
    )
    soap.finish_upload_file_list_v2.return_value = [
        MagicMock(filename="pay.xml", hash="a" * 64, status=UploadFinishStatus.I, ticket_id="T2")
    ]
    fp = tmp_path / "pay.xml"
    fp.write_text("<p/>")
    result = client.upload_payment_batch(
        file=fp,
        metadata=UploadFile(filename="pay.xml", format="XML SEPA", mode=UploadMode.AllOrNothing),
    )
    assert result is not None
    assert result.status == UploadFinishStatus.I
