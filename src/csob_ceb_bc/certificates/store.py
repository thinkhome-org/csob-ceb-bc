from __future__ import annotations

import ssl
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

from csob_ceb_bc.config import CertificateConfig
from csob_ceb_bc.errors import CsobBCCertificateError


class CertificateStore:
    """Loads and validates certificates, builds mTLS-capable HTTP clients."""

    def __init__(self, config: CertificateConfig) -> None:
        self._config = config
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self.cert_path: Path
        self.key_path: Path
        self._load()

    def _load(self) -> None:
        if self._config.pfx_file:
            self._extract_pfx()
        else:
            self.cert_path = self._config.cert_file  # type: ignore[assignment]
            self.key_path = self._config.key_file  # type: ignore[assignment]

        if not self.cert_path.exists():
            raise CsobBCCertificateError(f"Certificate not found: {self.cert_path}")
        if not self.key_path.exists():
            raise CsobBCCertificateError(f"Private key not found: {self.key_path}")

    @property
    def _cert(self) -> x509.Certificate:
        return x509.load_pem_x509_certificate(
            self.cert_path.read_bytes(), default_backend()
        )

    @property
    def fingerprint(self) -> str:
        return self._cert.fingerprint(hashes.SHA256()).hex()

    @property
    def subject(self) -> str:
        return str(self._cert.subject)

    @property
    def not_after(self) -> datetime:
        na = self._cert.not_valid_after_utc
        if na is None:
            raise CsobBCCertificateError("Certificate has no expiry date")
        return na

    def _extract_pfx(self) -> None:
        import os

        from cryptography.hazmat.primitives import serialization

        pfx_path = self._config.pfx_file
        if pfx_path is None:
            raise CsobBCCertificateError("pfx_file is None")  # pragma: no cover
        password_env = self._config.pfx_password_env or "CSOB_BC_PFX_PASSWORD"
        password = os.environ.get(password_env, "").encode() or None

        try:
            with open(pfx_path, "rb") as f:
                pfx_data = f.read()
            from cryptography.hazmat.primitives.serialization import pkcs12

            private_key, cert, _ = pkcs12.load_key_and_certificates(
                pfx_data, password, default_backend()
            )
            if private_key is None or cert is None:
                raise CsobBCCertificateError("PFX does not contain key or certificate")

            self._temp_dir = tempfile.TemporaryDirectory()
            base = Path(self._temp_dir.name)
            self.cert_path = base / "cert.pem"
            self.key_path = base / "key.pem"

            self.cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            self.key_path.write_bytes(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
            self.key_path.chmod(0o600)
        except Exception as exc:
            raise CsobBCCertificateError(f"Failed to load PFX: {exc}") from exc

    def validate_not_expiring(self, min_days: int = 7) -> None:
        try:
            pem = self.cert_path.read_bytes()
            cert = x509.load_pem_x509_certificate(pem, default_backend())
            if cert.not_valid_after_utc is None:
                raise CsobBCCertificateError("Certificate has no expiry date")
            days_left = (cert.not_valid_after_utc - datetime.now(UTC)).days
            if days_left < min_days:
                raise CsobBCCertificateError(
                    f"Certificate expires in {days_left} days (minimum {min_days})",
                    permanent=False,
                    retryable=False,
                )
        except CsobBCCertificateError:
            raise
        except Exception as exc:
            raise CsobBCCertificateError(f"Certificate validation failed: {exc}") from exc

    def validate_certificate(self) -> None:
        """Verify certificate meets ČSOB requirements (SHA256+, RSA 2048+, KU/EKU if present)."""
        try:
            pem = self.cert_path.read_bytes()
            cert = x509.load_pem_x509_certificate(pem, default_backend())

            # Signature algorithm must be SHA256 or stronger
            hash_alg = cert.signature_hash_algorithm
            if hash_alg is None or hash_alg.digest_size < 32:
                raise CsobBCCertificateError(
                    "Certificate signature must be SHA256 or stronger",
                    permanent=True,
                    retryable=False,
                )

            # Key must be RSA 2048+
            public_key = cert.public_key()
            if not hasattr(public_key, "key_size"):
                raise CsobBCCertificateError(
                    "Certificate public key must be RSA",
                    permanent=True,
                    retryable=False,
                )
            if public_key.key_size < 2048:
                raise CsobBCCertificateError(
                    f"RSA key size must be at least 2048 bits, got {public_key.key_size}",
                    permanent=True,
                    retryable=False,
                )

            # Key Usage (if present): Digital Signature or Key Encipherment
            try:
                key_usage = cert.extensions.get_extension_for_class(x509.KeyUsage)
                if not (key_usage.value.digital_signature or key_usage.value.key_encipherment):
                    raise CsobBCCertificateError(
                        "Certificate KeyUsage must include DigitalSignature or KeyEncipherment",
                        permanent=True,
                        retryable=False,
                    )
            except x509.ExtensionNotFound:
                pass

            # Extended Key Usage (if present): Client Authentication
            try:
                eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
                client_auth_oid = x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH
                if client_auth_oid not in eku.value:
                    raise CsobBCCertificateError(
                        "Certificate ExtendedKeyUsage must include Client Authentication",
                        permanent=True,
                        retryable=False,
                    )
            except x509.ExtensionNotFound:
                pass

        except CsobBCCertificateError:
            raise
        except Exception as exc:
            raise CsobBCCertificateError(
                f"Certificate validation failed: {exc}",
                permanent=True,
                retryable=False,
            ) from exc

    def _build_ssl_context(self, verify: bool | str = True) -> ssl.SSLContext:
        if verify is False:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        else:
            context = ssl.create_default_context()
            if isinstance(verify, str):
                context.load_verify_locations(verify)
            elif self._config.ca_bundle:
                context.load_verify_locations(str(self._config.ca_bundle))
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(str(self.cert_path), str(self.key_path))
        return context

    def build_httpx_client(self, verify: bool | str = True) -> httpx.Client:
        return httpx.Client(verify=self._build_ssl_context(verify))

    def build_async_httpx_client(self, verify: bool | str = True) -> httpx.AsyncClient:
        return httpx.AsyncClient(verify=self._build_ssl_context(verify))

    def __del__(self) -> None:
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
