from __future__ import annotations

import hashlib
from pathlib import Path

from csob_ceb_bc.certificates.store import CertificateStore
from csob_ceb_bc.config import ConnectorConfig
from csob_ceb_bc.downloads.manager import DownloadManager
from csob_ceb_bc.import_protocols.manager import ImportProtocolManager
from csob_ceb_bc.models import (
    DownloadFile,
    DownloadFilter,
    UploadFile,
    UploadFinishResult,
)
from csob_ceb_bc.rest.transfer import RestTransferClient
from csob_ceb_bc.soap.gateway import SoapGateway
from csob_ceb_bc.state.sqlite_repo import SqliteStateRepository
from csob_ceb_bc.uploads.manager import UploadManager
from csob_ceb_bc.rate_limit import TokenBucketRateLimiter
from csob_ceb_bc.metrics import MetricsCollector


class BusinessConnectorClient:
    """Public facade for ČSOB CEB Business Connector SDK."""

    def __init__(
        self,
        *,
        config: ConnectorConfig,
        soap: SoapGateway,
        rest: RestTransferClient,
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
            client_app_guid=config.client_app_guid,
            soap=soap,
            rest=rest,
            state=state,
            metrics=self._metrics,
        )

    @classmethod
    def from_config(cls, config: ConnectorConfig) -> "BusinessConnectorClient":
        cert_store = CertificateStore(config.certificate)
        cert_store.validate_not_expiring()
        state = SqliteStateRepository(config.state_url)
        rate_limiter = TokenBucketRateLimiter(
            capacity=config.rate_limit.soap_calls,
            refill_per_second=config.rate_limit.soap_calls / config.rate_limit.per_seconds,
        )
        soap = SoapGateway(config, rate_limiter=rate_limiter)
        rest = RestTransferClient(
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

    def list_available_files(self, filter: DownloadFilter) -> list[DownloadFile]:
        return self._download_manager.list_available_files(filter)

    def download_new_files(
        self,
        filter: DownloadFilter,
        target_dir: Path,
    ) -> list[DownloadFile]:
        return self._download_manager.download_new_files(filter, target_dir)

    def upload_payment_batch(
        self,
        file: Path,
        metadata: UploadFile,
    ) -> UploadFinishResult | None:
        return self._upload_manager.upload_payment_batch(file, metadata)

    def poll_import_protocols(self, target_dir: Path | None = None) -> list[DownloadFile]:
        if target_dir is None:
            target_dir = Path(".")
        return self._import_protocol_manager.poll_import_protocols(target_dir)

    def resume_pending(self) -> None:
        """Resume any pending uploads or downloads after a crash."""
        self._upload_manager.resume_pending()

    def metrics_snapshot(self) -> dict:
        """Return current metrics snapshot."""
        return self._metrics.snapshot()
