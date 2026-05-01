from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    PRODUCTION = "production"
    DEMO = "demo"


class TimeoutsConfig(BaseModel):
    connect_seconds: float = 10.0
    read_seconds: float = 120.0
    write_seconds: float = 120.0
    pool_seconds: float = 10.0


class RateLimitConfig(BaseModel):
    soap_calls: int = 30
    per_seconds: int = 1200
    default_poll_seconds: int = 60
    short_poll_seconds: int = 10


class LoggingConfig(BaseModel):
    level: str = "INFO"
    redact_contract_number: bool = True


class CertificateConfig(BaseModel):
    cert_file: Path | None = None
    key_file: Path | None = None
    ca_bundle: Path | None = None
    pfx_file: Path | None = None
    pfx_password_env: str | None = None

    @model_validator(mode="after")
    def _cert_or_pfx(self) -> CertificateConfig:
        has_pem = self.cert_file is not None and self.key_file is not None
        has_pfx = self.pfx_file is not None
        if not has_pem and not has_pfx:
            raise ValueError("Either cert_file+key_file or pfx_file must be provided")
        return self


class ConnectorConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CSOB_BC_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    environment: Environment = Environment.PRODUCTION
    contract_number: str = Field(default="")
    client_app_guid: str = Field(default="")
    certificate: CertificateConfig
    state_url: str = "sqlite:///csob_ceb_state.db"
    timeouts: TimeoutsConfig = Field(default_factory=TimeoutsConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @field_validator("client_app_guid")
    @classmethod
    def _guid_format(cls, v: str) -> str:
        import re

        if not re.fullmatch(
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
            v,
        ):
            raise ValueError(
                "client_app_guid must be a UUID in format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )
        return v

    @field_validator("contract_number")
    @classmethod
    def _contract_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("contract_number is required")
        return v
