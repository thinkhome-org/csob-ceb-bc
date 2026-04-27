import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from csob_ceb_bc.config import Environment, CertificateConfig, ConnectorConfig


def test_environment_enum():
    assert Environment.PRODUCTION == "production"
    assert Environment.DEMO == "demo"


def test_certificate_config_pem():
    cfg = CertificateConfig(cert_file=Path("/etc/cert.crt"), key_file=Path("/etc/key.key"))
    assert cfg.cert_file == Path("/etc/cert.crt")
    assert cfg.key_file == Path("/etc/key.key")


def test_certificate_config_pfx():
    cfg = CertificateConfig(pfx_file=Path("/etc/cert.pfx"), pfx_password_env="PASS")
    assert cfg.pfx_file == Path("/etc/cert.pfx")
    assert cfg.pfx_password_env == "PASS"


def test_certificate_config_requires_cert_or_pfx():
    with pytest.raises(ValidationError):
        CertificateConfig()


def test_connector_config_defaults():
    cfg = ConnectorConfig(
        environment=Environment.PRODUCTION,
        contract_number="123456",
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        certificate=CertificateConfig(cert_file=Path("c.crt"), key_file=Path("k.key")),
    )
    assert cfg.contract_number == "123456"
    assert cfg.timeouts.connect_seconds == 10
    assert cfg.timeouts.read_seconds == 120


def test_connector_config_env_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CSOB_BC_CONTRACT_NUMBER", "999999")
    monkeypatch.setenv("CSOB_BC_ENVIRONMENT", "demo")
    cfg = ConnectorConfig(
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        certificate=CertificateConfig(cert_file=Path("c.crt"), key_file=Path("k.key")),
    )
    assert cfg.contract_number == "999999"
    assert cfg.environment == Environment.DEMO
