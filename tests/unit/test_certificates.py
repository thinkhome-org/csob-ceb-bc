"""Tests for CertificateStore."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from csob_ceb_bc.certificates.store import CertificateStore
from csob_ceb_bc.config import CertificateConfig
from csob_ceb_bc.errors import CsobBCCertificateError

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_load_pem_success():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "test.key",
        )
    )
    assert store.cert_path.exists()
    assert store.key_path.exists()
    store.validate_not_expiring(min_days=1)


def test_missing_cert():
    with pytest.raises(CsobBCCertificateError) as exc_info:
        CertificateStore(
            CertificateConfig(
                cert_file=Path("/nonexistent/cert.pem"),
                key_file=FIXTURES / "certs" / "test.key",
            )
        )
    assert "not found" in str(exc_info.value).lower()


def test_missing_key():
    with pytest.raises(CsobBCCertificateError) as exc_info:
        CertificateStore(
            CertificateConfig(
                cert_file=FIXTURES / "certs" / "test.pem",
                key_file=Path("/nonexistent/key.pem"),
            )
        )
    assert "not found" in str(exc_info.value).lower()


def test_build_client_with_ca_bundle():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "test.key",
            ca_bundle=FIXTURES / "certs" / "test.pem",
        )
    )
    client = store.build_httpx_client()
    assert client is not None


def test_build_client_verify_false():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "test.key",
        )
    )
    client = store.build_httpx_client(verify=False)
    assert client is not None


def test_build_client_verify_str():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "test.key",
        )
    )
    client = store.build_httpx_client(verify=str(FIXTURES / "certs" / "test.pem"))
    assert client is not None


def test_validate_corrupted_cert(tmp_path: Path):
    cert_file = tmp_path / "bad.pem"
    cert_file.write_text("not a valid cert")
    key_file = tmp_path / "bad.key"
    key_file.write_text("not a valid key")
    store = CertificateStore(CertificateConfig(cert_file=cert_file, key_file=key_file))
    with pytest.raises(CsobBCCertificateError) as exc_info:
        store.validate_not_expiring()
    assert "validation failed" in str(exc_info.value).lower()


def test_build_async_httpx_client():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "test.key",
        )
    )
    client = store.build_async_httpx_client()
    assert client is not None


def test_build_async_httpx_client_verify_false():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "test.key",
        )
    )
    client = store.build_async_httpx_client(verify=False)
    assert client is not None


def test_build_async_httpx_client_verify_str():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "test.key",
        )
    )
    client = store.build_async_httpx_client(verify=str(FIXTURES / "certs" / "test.pem"))
    assert client is not None


def test_pfx_cleanup_on_del():
    store = CertificateStore(
        CertificateConfig(
            pfx_file=FIXTURES / "certs" / "test.pfx",
            pfx_password_env="NONEXISTENT_ENV_FOR_TEST",
        )
    )
    temp_dir = Path(store.cert_path).parent
    assert temp_dir.exists()
    del store
    assert not temp_dir.exists()


def test_validate_no_expiry_date():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "test.key",
        )
    )
    mock_cert = MagicMock()
    mock_cert.not_valid_after_utc = None
    with (
        patch(
            "csob_ceb_bc.certificates.store.x509.load_pem_x509_certificate",
            return_value=mock_cert,
        ),
        pytest.raises(CsobBCCertificateError) as exc_info,
    ):
        store.validate_not_expiring()
    assert "no expiry date" in str(exc_info.value).lower()


def test_validate_expiring_soon():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "test.key",
        )
    )
    from datetime import UTC, datetime, timedelta

    now = datetime(2030, 1, 1, 0, 0, 0, tzinfo=UTC)
    mock_cert = MagicMock()
    mock_cert.not_valid_after_utc = now + timedelta(days=3)
    with (
        patch(
            "csob_ceb_bc.certificates.store.x509.load_pem_x509_certificate",
            return_value=mock_cert,
        ),
        patch("csob_ceb_bc.certificates.store.datetime") as mock_datetime,
        pytest.raises(CsobBCCertificateError) as exc_info,
    ):
        mock_datetime.now.return_value = now
        store.validate_not_expiring()
    assert "expires in 3 days" in str(exc_info.value).lower()


def test_validate_certificate_key_encipherment_ok():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "valid.pem",
            key_file=FIXTURES / "certs" / "valid.key",
        )
    )
    mock_cert = MagicMock()
    mock_hash_alg = MagicMock()
    mock_hash_alg.digest_size = 32
    mock_cert.signature_hash_algorithm = mock_hash_alg
    mock_pk = MagicMock()
    mock_pk.key_size = 2048
    mock_cert.public_key.return_value = mock_pk
    from cryptography import x509

    ku_ext = x509.extensions.Extension(
        x509.ObjectIdentifier("2.5.29.15"),
        critical=False,
        value=x509.KeyUsage(
            digital_signature=False,
            content_commitment=False,
            key_encipherment=True,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False,
        ),
    )
    eku_ext = x509.extensions.Extension(
        x509.ObjectIdentifier("2.5.29.37"),
        critical=False,
        value=x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),
    )
    mock_cert.extensions.get_extension_for_class.side_effect = [ku_ext, eku_ext]
    with patch(
        "csob_ceb_bc.certificates.store.x509.load_pem_x509_certificate",
        return_value=mock_cert,
    ):
        store.validate_certificate()


def test_validate_certificate_success():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "valid.pem",
            key_file=FIXTURES / "certs" / "valid.key",
        )
    )
    store.validate_certificate()


def test_validate_certificate_missing_ku_and_eku_ok():
    # Manual says KU and EKU are optional ("pokud je přítomno")
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "test.key",
        )
    )
    store.validate_certificate()


def test_validate_certificate_bad_sig():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "valid.pem",
            key_file=FIXTURES / "certs" / "valid.key",
        )
    )
    mock_cert = MagicMock()
    mock_hash_alg = MagicMock()
    mock_hash_alg.digest_size = 20  # SHA-1
    mock_cert.signature_hash_algorithm = mock_hash_alg
    with (
        patch(
            "csob_ceb_bc.certificates.store.x509.load_pem_x509_certificate",
            return_value=mock_cert,
        ),
        pytest.raises(CsobBCCertificateError) as exc_info,
    ):
        store.validate_certificate()
    assert "SHA256" in str(exc_info.value)


def test_validate_certificate_small_key():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "valid.pem",
            key_file=FIXTURES / "certs" / "valid.key",
        )
    )
    mock_cert = MagicMock()
    mock_hash_alg = MagicMock()
    mock_hash_alg.digest_size = 32
    mock_cert.signature_hash_algorithm = mock_hash_alg
    mock_pk = MagicMock()
    mock_pk.key_size = 1024
    mock_cert.public_key.return_value = mock_pk
    with (
        patch(
            "csob_ceb_bc.certificates.store.x509.load_pem_x509_certificate",
            return_value=mock_cert,
        ),
        pytest.raises(CsobBCCertificateError) as exc_info,
    ):
        store.validate_certificate()
    assert "2048" in str(exc_info.value)


def test_validate_certificate_no_eku_ok():
    # Manual says EKU is optional ("pokud je přítomno")
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "valid.pem",
            key_file=FIXTURES / "certs" / "valid.key",
        )
    )
    mock_cert = MagicMock()
    mock_hash_alg = MagicMock()
    mock_hash_alg.digest_size = 32
    mock_cert.signature_hash_algorithm = mock_hash_alg
    mock_pk = MagicMock()
    mock_pk.key_size = 2048
    mock_cert.public_key.return_value = mock_pk
    from cryptography import x509

    ku_ext = x509.extensions.Extension(
        x509.ObjectIdentifier("2.5.29.15"),
        critical=False,
        value=x509.KeyUsage(
            digital_signature=True,
            content_commitment=False,
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False,
        ),
    )
    mock_cert.extensions.get_extension_for_class.side_effect = [
        ku_ext,
        x509.ExtensionNotFound("No EKU", x509.ObjectIdentifier("2.5.29.37")),
    ]
    with patch(
        "csob_ceb_bc.certificates.store.x509.load_pem_x509_certificate",
        return_value=mock_cert,
    ):
        store.validate_certificate()


def test_validate_certificate_non_rsa_key():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "valid.pem",
            key_file=FIXTURES / "certs" / "valid.key",
        )
    )
    mock_cert = MagicMock()
    mock_hash_alg = MagicMock()
    mock_hash_alg.digest_size = 32
    mock_cert.signature_hash_algorithm = mock_hash_alg
    mock_pk = MagicMock(spec=[])
    mock_cert.public_key.return_value = mock_pk
    with (
        patch(
            "csob_ceb_bc.certificates.store.x509.load_pem_x509_certificate",
            return_value=mock_cert,
        ),
        pytest.raises(CsobBCCertificateError) as exc_info,
    ):
        store.validate_certificate()
    assert "RSA" in str(exc_info.value)


def test_validate_certificate_no_digital_signature():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "valid.pem",
            key_file=FIXTURES / "certs" / "valid.key",
        )
    )
    mock_cert = MagicMock()
    mock_hash_alg = MagicMock()
    mock_hash_alg.digest_size = 32
    mock_cert.signature_hash_algorithm = mock_hash_alg
    mock_pk = MagicMock()
    mock_pk.key_size = 2048
    mock_cert.public_key.return_value = mock_pk
    from cryptography import x509

    ku_ext = x509.extensions.Extension(
        x509.ObjectIdentifier("2.5.29.15"),
        critical=False,
        value=x509.KeyUsage(
            digital_signature=False,
            content_commitment=False,
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False,
        ),
    )
    mock_cert.extensions.get_extension_for_class.side_effect = [
        ku_ext,
        x509.ExtensionNotFound("No EKU", x509.ObjectIdentifier("2.5.29.37")),
    ]
    with (
        patch(
            "csob_ceb_bc.certificates.store.x509.load_pem_x509_certificate",
            return_value=mock_cert,
        ),
        pytest.raises(CsobBCCertificateError) as exc_info,
    ):
        store.validate_certificate()
    assert "DigitalSignature" in str(exc_info.value)


def test_validate_certificate_eku_without_client_auth():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "valid.pem",
            key_file=FIXTURES / "certs" / "valid.key",
        )
    )
    mock_cert = MagicMock()
    mock_hash_alg = MagicMock()
    mock_hash_alg.digest_size = 32
    mock_cert.signature_hash_algorithm = mock_hash_alg
    mock_pk = MagicMock()
    mock_pk.key_size = 2048
    mock_cert.public_key.return_value = mock_pk
    from cryptography import x509

    ku_ext = x509.extensions.Extension(
        x509.ObjectIdentifier("2.5.29.15"),
        critical=False,
        value=x509.KeyUsage(
            digital_signature=True,
            content_commitment=False,
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False,
        ),
    )
    eku_ext = x509.extensions.Extension(
        x509.ObjectIdentifier("2.5.29.37"),
        critical=False,
        value=x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
    )
    mock_cert.extensions.get_extension_for_class.side_effect = [
        ku_ext,
        eku_ext,
    ]
    with (
        patch(
            "csob_ceb_bc.certificates.store.x509.load_pem_x509_certificate",
            return_value=mock_cert,
        ),
        pytest.raises(CsobBCCertificateError) as exc_info,
    ):
        store.validate_certificate()
    assert "Client Authentication" in str(exc_info.value)


def test_validate_key_matches_cert_success():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "valid.pem",
            key_file=FIXTURES / "certs" / "valid.key",
        )
    )
    store.validate_key_matches_cert()


def test_validate_key_matches_cert_mismatch():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "test.pem",
            key_file=FIXTURES / "certs" / "valid.key",
        )
    )
    with pytest.raises(CsobBCCertificateError) as exc_info:
        store.validate_key_matches_cert()
    assert "does not match" in str(exc_info.value).lower()


def test_validate_key_matches_cert_corrupted_key(tmp_path: Path):
    bad_key = tmp_path / "bad.key"
    bad_key.write_text("not a valid key")
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "valid.pem",
            key_file=bad_key,
        )
    )
    with pytest.raises(CsobBCCertificateError) as exc_info:
        store.validate_key_matches_cert()
    assert "validation failed" in str(exc_info.value).lower()


def test_validate_certificate_unexpected_error():
    store = CertificateStore(
        CertificateConfig(
            cert_file=FIXTURES / "certs" / "valid.pem",
            key_file=FIXTURES / "certs" / "valid.key",
        )
    )
    with (
        patch(
            "csob_ceb_bc.certificates.store.x509.load_pem_x509_certificate",
            side_effect=RuntimeError("boom"),
        ),
        pytest.raises(CsobBCCertificateError) as exc_info,
    ):
        store.validate_certificate()
    assert "validation failed" in str(exc_info.value).lower()
