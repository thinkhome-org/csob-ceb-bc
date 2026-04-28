from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

from csob_ceb_bc.logging import get_logger
from csob_ceb_bc.metrics import MetricsCollector, timed
from csob_ceb_bc.models import DownloadBatchResult, DownloadFile, DownloadFileStatus, DownloadFilter
from csob_ceb_bc.redaction import redact_contract
from csob_ceb_bc.rest.async_transfer import AsyncRestTransferClient
from csob_ceb_bc.soap.async_gateway import AsyncSoapGateway
from csob_ceb_bc.state.base import StateRepository

logger = get_logger("csob_ceb_bc.downloads")


class DownloadManager:
    def __init__(
        self,
        *,
        contract_number: str,
        client_app_guid: str,
        cert_fingerprint: str,
        environment: str,
        soap: AsyncSoapGateway,
        rest: AsyncRestTransferClient,
        state: StateRepository,
        metrics: MetricsCollector | None = None,
    ) -> None:
        self._contract_number = contract_number
        self._client_app_guid = client_app_guid
        self._cert_fingerprint = cert_fingerprint
        self._environment = environment
        self._soap = soap
        self._rest = rest
        self._state = state
        self._metrics = metrics

    def _profile_key(self, filter: DownloadFilter) -> str:
        parts = [
            self._environment,
            self._contract_number,
            self._client_app_guid,
            self._cert_fingerprint,
        ]
        if filter.file_types:
            parts.append("_".join(sorted(ft.value for ft in filter.file_types)))
        if filter.file_formats:
            parts.append("_".join(sorted(filter.file_formats)))
        if filter.filename:
            parts.append(filter.filename)
        if filter.created_after is not None:
            parts.append(filter.created_after.isoformat())
        if filter.created_before is not None:
            parts.append(filter.created_before.isoformat())
        raw = ":".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _ensure_filter_guid(self, filter: DownloadFilter) -> DownloadFilter:
        if filter.client_app_guid is None:
            return filter.model_copy(update={"client_app_guid": self._client_app_guid})
        return filter

    async def list_available_files(self, filter: DownloadFilter) -> list[DownloadFile]:
        filter = self._ensure_filter_guid(filter)
        key = self._profile_key(filter)
        prev = await asyncio.to_thread(self._state.get_profile_cursor, key)
        result = await self._soap.get_download_file_list_v4(
            prev_query_timestamp=prev,
            filter=filter,
        )
        return result.files

    async def download_new_files(
        self,
        filter: DownloadFilter,
        target_dir: Path,
    ) -> DownloadBatchResult:
        from csob_ceb_bc.errors import CsobBCHttpError

        await asyncio.to_thread(target_dir.mkdir, parents=True, exist_ok=True)
        filter = self._ensure_filter_guid(filter)
        key = self._profile_key(filter)
        prev = await asyncio.to_thread(self._state.get_profile_cursor, key)
        log_ctx = logger.bind(
            contract_redacted=redact_contract(self._contract_number),
            profile_key=key,
        )
        log_ctx.info("download_start", prev_query_timestamp=prev.isoformat() if prev else None)
        result = await self._soap.get_download_file_list_v4(
            prev_query_timestamp=prev,
            filter=filter,
        )
        log_ctx.info("download_soap_complete", file_count=len(result.files))
        if self._metrics:
            self._metrics.inc("download_soap_calls")
            self._metrics.gauge("download_file_count", len(result.files))

        downloaded: list[DownloadFile] = []
        pending: list[DownloadFile] = []
        failed: list[DownloadFile] = []

        for file in result.files:
            if file.status == DownloadFileStatus.F:
                # permanent failure — log and skip, does NOT block cursor
                failed.append(file)
                log_ctx.info("download_file_permanent_failure", filename=file.filename)
                continue
            if file.status == DownloadFileStatus.R or file.url is None:
                pending.append(file)
                log_ctx.info(
                    "download_file_unresolved",
                    filename=file.filename,
                    status=file.status.value,
                )
                continue
            if file.status == DownloadFileStatus.D and file.url:
                local_path = target_dir / file.filename
                try:
                    if self._metrics:
                        with timed(self._metrics, "download_latency_seconds"):
                            await self._rest.download_to_file(file.url, local_path)
                    else:
                        await self._rest.download_to_file(file.url, local_path)
                except CsobBCHttpError as exc:
                    if exc.permanent:
                        failed.append(file)
                        log_ctx.warning(
                            "download_file_permanent_rest_error",
                            filename=file.filename,
                            error=exc.safe_message,
                        )
                        continue
                    raise
                downloaded.append(file)
                if self._metrics:
                    self._metrics.inc("download_success")
                log_ctx.info(
                    "download_file_success",
                    filename=file.filename,
                    local_path=str(local_path),
                )

        cursor_advanced = len(pending) == 0
        if cursor_advanced:
            await asyncio.to_thread(self._state.set_profile_cursor, key, result.query_timestamp)
            log_ctx.info(
                "download_cursor_advanced",
                query_timestamp=result.query_timestamp.isoformat(),
                downloaded_count=len(downloaded),
            )

        if pending and self._metrics:
            self._metrics.inc("download_unresolved_files", len(pending))

        return DownloadBatchResult(
            downloaded=downloaded,
            pending=pending,
            failed=failed,
            cursor_advanced=cursor_advanced,
            query_timestamp=result.query_timestamp,
        )
