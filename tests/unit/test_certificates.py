from pathlib import Path

import pytest
import httpx

from csob_ceb_bc.certificates.store import CertificateStore
from csob_ceb_bc.config import CertificateConfig
from csob_ceb_bc.errors import CsobBCCertificateError


FIXTURES = Path(__file__).parent.parent / "fixtures" / "certs"


def test_load_pem_pair():
    cfg = CertificateConfig(
        cert_file=FIXTURES / "test.pem",
        key_file=FIXTURES / "test.key",
    )
    store = CertificateStore(cfg)
    assert store.cert_path.exists()
    assert store.key_path.exists()


def test_validate_not_expiring():
    cfg = CertificateConfig(
        cert_file=FIXTURES / "test.pem",
        key_file=FIXTURES / "test.key",
    )
    store = CertificateStore(cfg)
    store.validate_not_expiring()  # should not raise


def test_build_httpx_client():
    cfg = CertificateConfig(
        cert_file=FIXTURES / "test.pem",
        key_file=FIXTURES / "test.key",
    )
    store = CertificateStore(cfg)
    client = store.build_httpx_client()
    assert isinstance(client, httpx.Client)
    client.close()


def test_missing_cert_raises():
    cfg = CertificateConfig(
        cert_file=Path("/nonexistent/cert.pem"),
        key_file=Path("/nonexistent/key.key"),
    )
    with pytest.raises(CsobBCCertificateError):
        CertificateStore(cfg)
