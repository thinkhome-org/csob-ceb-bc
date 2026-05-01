"""Async version of ImportProtocolManager."""

from __future__ import annotations

import hashlib
from pathlib import Path

from csob_ceb_bc.errors import CsobBCHttpError
from csob_ceb_bc.logging import get_logger
from csob_ceb_bc.metrics import MetricsCollector, timed
from csob_ceb_bc.models import (
    DownloadBatchResult,
    DownloadFile,
    DownloadFileStatus,
    DownloadFileType,
    DownloadFilter,
)
from csob_ceb_bc.rest.async_transfer import AsyncRestTransferClient
from csob_ceb_bc.soap.gateway import SoapGateway
from csob_ceb_bc.state.base import StateRepository

logger = get_logger("csob_ceb_bc.import_protocols")


class AsyncImportProtocolManager:
    def __init__(
        self,
        *,
        contract_number: str,
        client_app_guid: str,
        environment: str,
        soap: SoapGateway,
        async_rest: AsyncRestTransferClient,
        state: StateRepository,
        metrics: MetricsCollector | None = None,
    ) -> None:
        self._contract_number = contract_number
        self._client_app_guid = client_app_guid
        self._environment = environment
        self._soap = soap
        self._async_rest = async_rest
        self._state = state
        self._metrics = metrics

    def _profile_key(self) -> str:
        raw = (
            f"{self._environment}:{self._contract_number}:{self._client_app_guid}:import_protocols"
        )
        return hashlib.sha256(raw.encode()).hexdigest()

    async def poll_import_protocols(self, target_dir: Path) -> DownloadBatchResult:
        target_dir.mkdir(parents=True, exist_ok=True)
        key = self._profile_key()
        prev = self._state.get_profile_cursor(key)
        result = self._soap.get_download_file_list_v4(
            prev_query_timestamp=prev,
            filter=DownloadFilter(
                file_types=[DownloadFileType.IMPPROT],
                client_app_guid=self._client_app_guid,
            ),
        )
        if self._metrics:
            self._metrics.inc("import_protocol_soap_calls")
            self._metrics.gauge("import_protocol_file_count", len(result.files))

        downloaded: list[DownloadFile] = []
        pending: list[DownloadFile] = []
        failed: list[DownloadFile] = []

        for file in result.files:
            if file.status == DownloadFileStatus.F:
                failed.append(file)
                logger.info("import_protocol_permanent_failure", filename=file.filename)
                continue
            if file.status == DownloadFileStatus.R or not file.url:
                pending.append(file)
                logger.info(
                    "import_protocol_unresolved",
                    filename=file.filename,
                    status=file.status.value,
                )
                continue
            if file.status == DownloadFileStatus.D and file.url:
                if not file.upload_file_hash:
                    pending.append(file)
                    logger.info(
                        "import_protocol_missing_hash",
                        filename=file.filename,
                    )
                    continue
                local_path = target_dir / file.filename
                try:
                    if self._metrics:
                        with timed(self._metrics, "import_protocol_download_latency_seconds"):
                            await self._async_rest.download_to_file(file.url, local_path)
                    else:
                        await self._async_rest.download_to_file(file.url, local_path)
                except CsobBCHttpError as exc:
                    if exc.permanent:
                        failed.append(file)
                        logger.warning(
                            "import_protocol_permanent_rest_error",
                            filename=file.filename,
                            error=exc.safe_message,
                        )
                        continue
                    raise
                downloaded.append(file)
                self._state.create_import_protocol(
                    new_file_id=file.filename,
                    upload_hash=file.upload_file_hash,
                    filename=file.filename,
                    client_app_guid=self._client_app_guid,
                )
                if self._metrics:
                    self._metrics.inc("import_protocol_download_success")

        cursor_advanced = len(pending) == 0
        if cursor_advanced:
            self._state.set_profile_cursor(key, result.query_timestamp)

        return DownloadBatchResult(
            downloaded=downloaded,
            pending=pending,
            failed=failed,
            cursor_advanced=cursor_advanced,
            query_timestamp=result.query_timestamp,
        )
