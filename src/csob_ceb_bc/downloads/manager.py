from __future__ import annotations

from pathlib import Path

from csob_ceb_bc.logging import get_logger
from csob_ceb_bc.metrics import MetricsCollector, timed
from csob_ceb_bc.models import DownloadFile, DownloadFileStatus, DownloadFilter
from csob_ceb_bc.redaction import redact_contract
from csob_ceb_bc.rest.transfer import RestTransferClient
from csob_ceb_bc.soap.gateway import SoapGateway
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
        soap: SoapGateway,
        rest: RestTransferClient,
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
        return ":".join(parts)

    def list_available_files(self, filter: DownloadFilter) -> list[DownloadFile]:
        key = self._profile_key(filter)
        prev = self._state.get_profile_cursor(key)
        result = self._soap.get_download_file_list_v4(
            prev_query_timestamp=prev,
            filter=filter,
        )
        return result.files

    def download_new_files(
        self,
        filter: DownloadFilter,
        target_dir: Path,
    ) -> list[DownloadFile]:
        target_dir.mkdir(parents=True, exist_ok=True)
        key = self._profile_key(filter)
        prev = self._state.get_profile_cursor(key)
        log_ctx = logger.bind(
            contract_redacted=redact_contract(self._contract_number),
            profile_key=key,
        )
        log_ctx.info("download_start", prev_query_timestamp=prev.isoformat() if prev else None)
        result = self._soap.get_download_file_list_v4(
            prev_query_timestamp=prev,
            filter=filter,
        )
        log_ctx.info("download_soap_complete", file_count=len(result.files))
        if self._metrics:
            self._metrics.inc("download_soap_calls")
            self._metrics.gauge("download_file_count", len(result.files))

        downloaded: list[DownloadFile] = []
        has_unresolved = False

        for file in result.files:
            if file.status == DownloadFileStatus.F:
                # permanent failure — log and skip, does NOT block cursor
                log_ctx.info("download_file_permanent_failure", filename=file.filename)
                continue
            if file.status == DownloadFileStatus.R or file.url is None:
                has_unresolved = True
                log_ctx.info(
                    "download_file_unresolved",
                    filename=file.filename,
                    status=file.status.value,
                )
                continue
            if file.status == DownloadFileStatus.D and file.url:
                local_path = target_dir / file.filename
                if self._metrics:
                    with timed(self._metrics, "download_latency_seconds"):
                        self._rest.download_to_file(file.url, local_path)
                else:
                    self._rest.download_to_file(file.url, local_path)
                downloaded.append(file)
                if self._metrics:
                    self._metrics.inc("download_success")
                log_ctx.info(
                    "download_file_success",
                    filename=file.filename,
                    local_path=str(local_path),
                )

        if not has_unresolved:
            self._state.set_profile_cursor(key, result.query_timestamp)
            log_ctx.info(
                "download_cursor_advanced",
                query_timestamp=result.query_timestamp.isoformat(),
                downloaded_count=len(downloaded),
            )

        if has_unresolved and self._metrics:
            unresolved = [
                f for f in result.files
                if f.status == DownloadFileStatus.R or f.url is None
            ]
            self._metrics.inc("download_unresolved_files", len(unresolved))

        return downloaded
