from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from csob_ceb_bc.soap.gateway import SoapGateway
from csob_ceb_bc.config import ConnectorConfig, CertificateConfig, Environment
from csob_ceb_bc.errors import CsobBCRateLimitError
from csob_ceb_bc.rate_limit import TokenBucketRateLimiter

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
def test_rate_limiter_blocks_when_empty(mock_client_cls: MagicMock):
    limiter = TokenBucketRateLimiter(capacity=0, refill_per_second=0.1)
    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"), rate_limiter=limiter)
    with pytest.raises(CsobBCRateLimitError):
        gw.get_download_file_list_v4()


@patch("csob_ceb_bc.soap.gateway.zeep.Client")
def test_rate_limiter_allows_when_available(mock_client_cls: MagicMock):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.service.GetDownloadFileList.return_value = {
        "QueryTimestamp": "2025-01-15T10:00:00+01:00",
        "FileList": None,
    }
    limiter = TokenBucketRateLimiter(capacity=1, refill_per_second=1.0)
    gw = SoapGateway(_config(), wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"), rate_limiter=limiter)
    result = gw.get_download_file_list_v4()
    assert result is not None
