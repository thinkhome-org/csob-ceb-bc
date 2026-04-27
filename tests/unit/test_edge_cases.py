"""Edge-case tests for robustness: timeouts, malformed responses, connection errors."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
import respx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from csob_ceb_bc.certificates.store import CertificateStore
from csob_ceb_bc.config import CertificateConfig
from csob_ceb_bc.errors import CsobBCCertificateError, CsobBCHttpError, CsobBCProtocolError
from csob_ceb_bc.rest.transfer import RestTransferClient
from csob_ceb_bc.soap.gateway import SoapGateway

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _store() -> CertificateStore:
    return CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "test.key",
        )
    )


# ---------------------------------------------------------------------------
# REST Transfer edge cases
# ---------------------------------------------------------------------------

@respx.mock
def test_upload_multipart_malformed_json():
    respx.post("https://example.com/upload").mock(
        return_value=httpx.Response(200, text="not-json")
    )
    client = RestTransferClient(cert_store=_store())
    file_path = FIXTURES / "certs" / "test.pem"
    with pytest.raises(CsobBCProtocolError) as exc_info:
        client.upload_multipart("https://example.com/upload", file_path, "test.pem")
    assert "non-JSON" in str(exc_info.value)


@respx.mock
def test_upload_multipart_malformed_schema():
    respx.post("https://example.com/upload").mock(
        return_value=httpx.Response(200, json={"unexpected": "field"})
    )
    client = RestTransferClient(cert_store=_store())
    file_path = FIXTURES / "certs" / "test.pem"
    with pytest.raises(CsobBCProtocolError) as exc_info:
        client.upload_multipart("https://example.com/upload", file_path, "test.pem")
    assert "schema" in str(exc_info.value).lower() or "JSON" in str(exc_info.value)


@respx.mock
def test_download_connection_timeout(tmp_path: Path):
    route = respx.get("https://example.com/file").mock(
        side_effect=httpx.ConnectTimeout("Connection timed out")
    )
    client = RestTransferClient(cert_store=_store())
    with pytest.raises(httpx.ConnectTimeout):
        client.download_to_file("https://example.com/file", tmp_path / "out.bin")
    assert route.called


@respx.mock
def test_download_read_timeout(tmp_path: Path):
    route = respx.get("https://example.com/file").mock(
        side_effect=httpx.ReadTimeout("Read timed out")
    )
    client = RestTransferClient(cert_store=_store())
    with pytest.raises(httpx.ReadTimeout):
        client.download_to_file("https://example.com/file", tmp_path / "out.bin")
    assert route.called


@respx.mock
def test_upload_connection_error():
    route = respx.post("https://example.com/upload").mock(
        side_effect=httpx.ConnectError("No route to host")
    )
    client = RestTransferClient(cert_store=_store())
    file_path = FIXTURES / "certs" / "test.pem"
    with pytest.raises(httpx.ConnectError):
        client.upload_multipart("https://example.com/upload", file_path, "test.pem")
    assert route.called


@respx.mock
def test_download_503_retryable():
    respx.get("https://example.com/file").mock(return_value=httpx.Response(503))
    client = RestTransferClient(cert_store=_store())
    with pytest.raises(CsobBCHttpError) as exc_info:
        client.download_to_file("https://example.com/file", Path("/dev/null"))
    assert exc_info.value.retryable is True
    assert exc_info.value.permanent is False


# ---------------------------------------------------------------------------
# Certificate edge cases
# ---------------------------------------------------------------------------

def test_certificate_missing_file():
    with pytest.raises(CsobBCCertificateError) as exc_info:
        CertificateStore(
            CertificateConfig(
                cert_file=Path("/nonexistent/cert.pem"),
                key_file=Path("/nonexistent/key.pem"),
            )
        )
    assert "not found" in str(exc_info.value).lower()


def test_certificate_expires_soon(tmp_path: Path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(days=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=3))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
        .sign(key, hashes.SHA256())
    )
    cert_file = tmp_path / "expired.pem"
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_file = tmp_path / "expired.key"
    key_file.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    store = CertificateStore(CertificateConfig(cert_file=cert_file, key_file=key_file))
    with pytest.raises(CsobBCCertificateError) as exc_info:
        store.validate_not_expiring(min_days=7)
    assert "expires in" in str(exc_info.value)
    assert exc_info.value.permanent is False


# ---------------------------------------------------------------------------
# SOAP Gateway edge cases
# ---------------------------------------------------------------------------

def test_soap_gateway_invalid_datetime_parsing(monkeypatch):
    config = MagicMock()
    config.environment = "DEMO"
    config.contract_number = "123456"
    config.certificate.cert_file = FIXTURES / "certs" / "test.pem"
    config.certificate.key_file = FIXTURES / "certs" / "test.key"
    config.certificate.ca_bundle = None

    gateway = SoapGateway(config, wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    assert gateway._parse_datetime("invalid-date") is None
    assert gateway._parse_datetime(None) is None
    assert gateway._parse_datetime("") is None


def test_soap_gateway_extract_ticket_id():
    config = MagicMock()
    config.environment = "DEMO"
    config.contract_number = "123456"
    config.certificate.cert_file = FIXTURES / "certs" / "test.pem"
    config.certificate.key_file = FIXTURES / "certs" / "test.key"
    config.certificate.ca_bundle = None

    gateway = SoapGateway(config, wsdl_path=str(FIXTURES / "soap" / "mock_wsdl.xml"))
    assert gateway._extract_ticket_id({"TicketId": "T-123"}) == "T-123"
    assert gateway._extract_ticket_id({"ticketId": "T-456"}) == "T-456"
    assert gateway._extract_ticket_id("not-a-dict") is None
