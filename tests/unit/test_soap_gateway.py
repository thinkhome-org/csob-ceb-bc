from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from csob_ceb_bc.config import CertificateConfig, ConnectorConfig, Environment
from csob_ceb_bc.errors import CsobBCRateLimitError
from csob_ceb_bc.models import DownloadFilter
from csob_ceb_bc.soap.gateway import SoapGateway

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
    )


@patch("csob_ceb_bc.soap.gateway.zeep.Client")
def test_get_download_file_list_v4(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.service.GetDownloadFileList.return_value = {
        "QueryTimestamp": "2025-01-15T10:00:00+01:00",
        "FileList": {
            "FileDetail": [
                {
                    "Url": "https://example.com/file1",
                    "Filename": "stmt.pdf",
                    "Type": "VYPIS",
                    "Format": "PDF",
                    "CreationDateTime": "2025-01-14T09:00:00+01:00",
                    "Size": 1024,
                    "UploadFileHash": None,
                    "Status": "D",
                }
            ]
        },
    }

    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    result = gw.get_download_file_list_v4(
        prev_query_timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        filter=DownloadFilter(file_types=["VYPIS"]),
    )
    assert result.query_timestamp is not None
    assert len(result.files) == 1
    assert result.files[0].filename == "stmt.pdf"
    assert result.files[0].status == "D"


@patch("csob_ceb_bc.soap.gateway.zeep.Client")
def test_soap_fault_mapped(mock_client_cls: MagicMock):
    from zeep.exceptions import Fault

    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.service.GetDownloadFileList.side_effect = Fault(
        "Rate limit",
        detail={"TicketId": "T-123", "FaultCode": "1101"},
    )

    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    with pytest.raises(CsobBCRateLimitError) as exc_info:
        gw.get_download_file_list_v4()
    assert exc_info.value.ticket_id == "T-123"
