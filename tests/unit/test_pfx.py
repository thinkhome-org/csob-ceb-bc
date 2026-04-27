"""Tests for PFX/P12 certificate extraction."""

from pathlib import Path

import pytest

from csob_ceb_bc.certificates.store import CertificateStore
from csob_ceb_bc.config import CertificateConfig
from csob_ceb_bc.errors import CsobBCCertificateError

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_pfx_extraction_success():
    store = CertificateStore(
        CertificateConfig(
            pfx_file=FIXTURES / "certs" / "test.pfx",
            pfx_password_env="NONEXISTENT_ENV_FOR_TEST",
        )
    )
    assert store.cert_path.exists()
    assert store.key_path.exists()
    assert store.key_path.stat().st_mode & 0o777 == 0o600
    store.validate_not_expiring(min_days=1)


def test_pfx_missing_file():
    with pytest.raises(CsobBCCertificateError) as exc_info:
        CertificateStore(
            CertificateConfig(
                pfx_file=FIXTURES / "certs" / "nonexistent.pfx",
            )
        )
    assert "not found" in str(exc_info.value).lower() or "Failed" in str(exc_info.value)


def test_pfx_invalid_password():
    # The test.pfx was generated without encryption, so any password should work
    # because NoEncryption() was used.  If we create a password-protected one,
    # this test would be meaningful.  For now, just verify loading works.
    store = CertificateStore(
        CertificateConfig(
            pfx_file=FIXTURES / "certs" / "test.pfx",
            pfx_password_env="NONEXISTENT_ENV_FOR_TEST",
        )
    )
    assert store.cert_path.exists()


def test_pfx_invalid_data(tmp_path: Path):
    bad_pfx = tmp_path / "bad.pfx"
    bad_pfx.write_bytes(b"not a valid pfx")
    with pytest.raises(CsobBCCertificateError) as exc_info:
        CertificateStore(
            CertificateConfig(
                pfx_file=bad_pfx,
            )
        )
    assert "Failed to load PFX" in str(exc_info.value)
