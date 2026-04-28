from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from csob_ceb_bc.certificates.store import CertificateStore
from csob_ceb_bc.config import ConnectorConfig, Environment
from csob_ceb_bc.downloads.manager import DownloadManager
from csob_ceb_bc.import_protocols.manager import ImportProtocolManager
from csob_ceb_bc.metrics import MetricsCollector
from csob_ceb_bc.models import (
    DownloadBatchResult,
    DownloadFile,
    DownloadFilter,
    UploadFile,
    UploadFinishResult,
)
from csob_ceb_bc.rate_limit import TokenBucketRateLimiter
from csob_ceb_bc.rest.async_transfer import AsyncRestTransferClient
from csob_ceb_bc.soap.async_gateway import AsyncSoapGateway
from csob_ceb_bc.soap.gateway import SoapGateway
from csob_ceb_bc.state.sqlite_repo import SqliteStateRepository
from csob_ceb_bc.uploads.manager import UploadManager


class BusinessConnectorClient:
    """Public facade for ČSOB CEB Business Connector SDK."""

    def __init__(
        self,
        *,
        config: ConnectorConfig,
        soap: AsyncSoapGateway,
        rest: AsyncRestTransferClient,
        state: SqliteStateRepository,
        cert_store: CertificateStore,
        metrics: MetricsCollector | None = None,
    ) -> None:
        self._config = config
        self._soap = soap
        self._rest = rest
        self._state = state
        self._cert_store = cert_store
        self._metrics = metrics or MetricsCollector()

        cert_pem = cert_store.cert_path.read_bytes()
        fingerprint = hashlib.sha256(cert_pem).hexdigest()[:16]

        self._download_manager = DownloadManager(
            contract_number=config.contract_number,
            client_app_guid=config.client_app_guid,
            cert_fingerprint=fingerprint,
            environment=config.environment.value,
            soap=soap,
            rest=rest,
            state=state,
            metrics=self._metrics,
        )
        self._upload_manager = UploadManager(
            contract_number=config.contract_number,
            client_app_guid=config.client_app_guid,
            soap=soap,
            rest=rest,
            state=state,
            metrics=self._metrics,
        )
        self._import_protocol_manager = ImportProtocolManager(
            contract_number=config.contract_number,
            client_app_guid=config.client_app_guid,
            environment=config.environment.value,
            soap=soap,
            rest=rest,
            state=state,
            metrics=self._metrics,
        )

    @classmethod
    def from_config(cls, config: ConnectorConfig) -> BusinessConnectorClient:
        cert_store = CertificateStore(config.certificate)
        cert_store.validate_certificate()
        cert_store.validate_key_matches_cert()
        cert_store.validate_not_expiring()
        state = SqliteStateRepository(config.state_url)
        rate_limiter = None
        if config.environment != Environment.DEMO:
            rate_limiter = TokenBucketRateLimiter(
                capacity=config.rate_limit.soap_calls,
                refill_per_second=config.rate_limit.soap_calls / config.rate_limit.per_seconds,
            )
        soap = AsyncSoapGateway(
            SoapGateway(config, rate_limiter=rate_limiter, cert_store=cert_store)
        )
        rest = AsyncRestTransferClient(
            cert_store=cert_store,
            timeout=None,  # uses defaults
        )
        return cls(
            config=config,
            soap=soap,
            rest=rest,
            state=state,
            cert_store=cert_store,
        )

    async def list_available_files(self, filter: DownloadFilter) -> list[DownloadFile]:
        return await self._download_manager.list_available_files(filter)

    async def download_new_files(
        self,
        filter: DownloadFilter,
        target_dir: Path,
    ) -> DownloadBatchResult:
        return await self._download_manager.download_new_files(filter, target_dir)

    async def upload_payment_batch(
        self,
        file: Path,
        metadata: UploadFile,
    ) -> UploadFinishResult | None:
        return await self._upload_manager.upload_payment_batch(file, metadata)

    async def poll_import_protocols(self, target_dir: Path | None = None) -> DownloadBatchResult:
        if target_dir is None:
            target_dir = Path(".")
        return await self._import_protocol_manager.poll_import_protocols(target_dir)

    async def resume_pending(self) -> list[UploadFinishResult]:
        """Resume any pending uploads or downloads after a crash."""
        return await self._upload_manager.resume_pending()

    def metrics_snapshot(self) -> dict[str, Any]:
        """Return current metrics snapshot."""
        return self._metrics.snapshot()
