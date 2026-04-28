from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from zeep.exceptions import Fault

from csob_ceb_bc.config import CertificateConfig, ConnectorConfig, Environment
from csob_ceb_bc.errors import (
    CsobBCPermanentError,
    CsobBCRateLimitError,
    CsobBCRetryableError,
)
from csob_ceb_bc.models import DownloadFilter, UploadFile, UploadMode
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


def _config_with_ca() -> ConnectorConfig:
    return ConnectorConfig(
        environment=Environment.DEMO,
        contract_number="123456",
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        certificate=CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "test.key",
            ca_bundle=FIXTURES / "certs" / "test.pem",
        ),
    )


@patch("csob_ceb_bc.soap.gateway.zeep.Client")
def test_get_download_file_list_v4(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.service.GetDownloadFileList_v2.return_value = {
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
def test_get_download_file_list_v4_missing_timestamp(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.service.GetDownloadFileList_v2.return_value = {
        "FileList": None,
    }

    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    result = gw.get_download_file_list_v4()
    assert result.query_timestamp is not None
    assert len(result.files) == 0


@patch("csob_ceb_bc.soap.gateway.zeep.Client")
def test_soap_fault_mapped(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.service.GetDownloadFileList_v2.side_effect = Fault(
        "Rate limit",
        detail={"TicketId": "T-123", "FaultCode": "1101"},
    )

    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    with pytest.raises(CsobBCRateLimitError) as exc_info:
        gw.get_download_file_list_v4()
    assert exc_info.value.ticket_id == "T-123"


@patch("csob_ceb_bc.soap.gateway.zeep.Client")
def test_start_upload_file_list_v3(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.service.StartUploadFileList_v3.return_value = {
        "FileStatus": [
            {
                "Filename": "pay.xml",
                "Status": "U",
                "Url": "https://example.com/upload",
                "TicketId": "T-456",
            }
        ]
    }

    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    result = gw.start_upload_file_list_v3(
        files=[
            UploadFile(
                filename="pay.xml",
                format="XML SEPA",
                mode=UploadMode.AllOrNothing,
                hash="a" * 64,
                size=1024,
            )
        ]
    )
    assert len(result) == 1
    assert result[0].filename == "pay.xml"
    assert result[0].status == "U"
    assert result[0].url == "https://example.com/upload"
    assert result[0].ticket_id == "T-456"


@patch("csob_ceb_bc.soap.gateway.zeep.Client")
def test_start_upload_single_status_not_list(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.service.StartUploadFileList_v3.return_value = {
        "FileStatus": {
            "Filename": "pay.xml",
            "Status": "R",
            "TicketId": "T-789",
        }
    }

    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    result = gw.start_upload_file_list_v3(
        files=[
            UploadFile(
                filename="pay.xml",
                format="XML SEPA",
                mode=UploadMode.AllOrNothing,
                hash="a" * 64,
                size=1024,
            )
        ]
    )
    assert len(result) == 1
    assert result[0].status == "R"


@patch("csob_ceb_bc.soap.gateway.zeep.Client")
def test_start_upload_fault(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.service.StartUploadFileList_v3.side_effect = Fault(
        "Blocked",
        detail={"TicketId": "T-999", "FaultCode": "1012"},
    )

    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    with pytest.raises(CsobBCPermanentError) as exc_info:
        gw.start_upload_file_list_v3(files=[])
    assert exc_info.value.ticket_id == "T-999"


@patch("csob_ceb_bc.soap.gateway.zeep.Client")
def test_finish_upload_file_list_v2(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.service.FinishUploadFileList_v2.return_value = {
        "FileList": {
            "FileStatus": [
                {
                    "Filename": "pay.xml",
                    "Hash": "a" * 64,
                    "Status": "I",
                    "TicketId": "T-100",
                }
            ]
        }
    }

    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    result = gw.finish_upload_file_list_v2(files=[("pay.xml", "a" * 64, "NFID-123")])
    assert len(result) == 1
    assert result[0].filename == "pay.xml"
    assert result[0].status == "I"
    assert result[0].ticket_id == "T-100"


@patch("csob_ceb_bc.soap.gateway.zeep.Client")
def test_finish_upload_single_status_not_list(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.service.FinishUploadFileList_v2.return_value = {
        "FileList": {
            "FileStatus": {
                "Filename": "pay.xml",
                "Hash": "a" * 64,
                "Status": "R",
                "TicketId": "T-101",
            }
        }
    }

    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    result = gw.finish_upload_file_list_v2(files=[("pay.xml", "a" * 64, "NFID-123")])
    assert len(result) == 1
    assert result[0].status == "R"


@patch("csob_ceb_bc.soap.gateway.zeep.Client")
def test_finish_upload_fault(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.service.FinishUploadFileList_v2.side_effect = Fault(
        "Error",
        detail={"TicketId": "T-102", "FaultCode": "1000"},
    )

    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    with pytest.raises(CsobBCRetryableError) as exc_info:
        gw.finish_upload_file_list_v2(files=[])
    assert exc_info.value.ticket_id == "T-102"


def test_parse_datetime_invalid():
    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    assert gw._parse_datetime("not-a-date") is None
    assert gw._parse_datetime(None) is None
    assert gw._parse_datetime("") is None


def test_extract_ticket_id():
    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    assert gw._extract_ticket_id({"TicketId": "T-1"}) == "T-1"
    assert gw._extract_ticket_id({"ticketId": "T-2"}) == "T-2"
    assert gw._extract_ticket_id("not-a-dict") is None
    assert gw._extract_ticket_id(None) is None


@patch("csob_ceb_bc.soap.gateway.zeep.Client")
def test_setup_transport_with_ca_bundle(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    config = _config_with_ca()
    gw = SoapGateway(config, wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    session = gw._transport.session
    assert session.verify == str(config.certificate.ca_bundle)


@patch("csob_ceb_bc.soap.gateway.zeep.Client")
def test_get_download_file_list_v4_full_filter(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.service.GetDownloadFileList_v2.return_value = {
        "QueryTimestamp": "2025-01-15T10:00:00+01:00",
        "TicketId": "T-FULL",
        "FileList": None,
    }

    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    from datetime import UTC

    result = gw.get_download_file_list_v4(
        filter=DownloadFilter(
            file_types=["VYPIS"],
            file_formats=["PDF", "CSV"],
            filename="stmt",
            created_after=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            created_before=datetime(2025, 1, 20, 0, 0, 0, tzinfo=UTC),
            client_app_guid="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        ),
    )
    call_args = mock_client.service.GetDownloadFileList_v2.call_args[1]
    assert call_args["Filter"]["FileTypes"] == {"FileType": ["VYPIS"]}
    assert call_args["Filter"]["FileFormats"] == {"FileFormat": ["PDF", "CSV"]}
    assert call_args["Filter"]["FileName"] == "stmt"
    assert call_args["Filter"]["CreatedAfter"] == "2025-01-01T00:00:00+00:00"
    assert call_args["Filter"]["CreatedBefore"] == "2025-01-20T00:00:00+00:00"
    assert call_args["Filter"]["ClientAppGuid"] == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    assert result.ticket_id == "T-FULL"


@patch("csob_ceb_bc.soap.gateway.zeep.Client")
def test_setup_transport_with_cert_store(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    from csob_ceb_bc.certificates.store import CertificateStore

    config = _config_with_ca()
    store = CertificateStore(config.certificate)
    gw = SoapGateway(config, wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"), cert_store=store)
    session = gw._transport.session
    assert session.cert == (str(store.cert_path), str(store.key_path))
    assert session.verify == str(config.certificate.ca_bundle)


@patch("csob_ceb_bc.soap.gateway.zeep.Client")
def test_get_download_file_list_v4_single_file_detail(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.service.GetDownloadFileList_v2.return_value = {
        "QueryTimestamp": "2025-01-15T10:00:00+01:00",
        "FileList": {
            "FileDetail": {
                "Filename": "stmt.pdf",
                "Type": "VYPIS",
                "Format": "PDF",
                "CreationDateTime": "2025-01-14T09:00:00+01:00",
                "Size": 1024,
                "UploadFileHash": None,
                "Status": "D",
                "TicketId": "T-SINGLE",
            }
        },
    }
    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    result = gw.get_download_file_list_v4()
    assert len(result.files) == 1
    assert result.files[0].ticket_id == "T-SINGLE"


@patch("csob_ceb_bc.soap.gateway.zeep.Client")
def test_get_download_file_list_v4_unparseable_creation_date(mock_client_cls: MagicMock):
    from csob_ceb_bc.errors import CsobBCProtocolError

    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.service.GetDownloadFileList_v2.return_value = {
        "QueryTimestamp": "2025-01-15T10:00:00+01:00",
        "FileList": {
            "FileDetail": {
                "Filename": "stmt.pdf",
                "Type": "VYPIS",
                "Format": "PDF",
                "CreationDateTime": "not-a-date",
                "Size": 1024,
                "UploadFileHash": None,
                "Status": "D",
            }
        },
    }
    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    with pytest.raises(CsobBCProtocolError) as exc_info:
        gw.get_download_file_list_v4()
    assert "CreationDateTime" in str(exc_info.value)
