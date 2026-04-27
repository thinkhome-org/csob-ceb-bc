from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from csob_ceb_bc.logging import get_logger
from csob_ceb_bc.metrics import MetricsCollector, timed
from csob_ceb_bc.models import (
    UploadFile,
    UploadFinishResult,
    UploadFinishStatus,
    UploadStartResult,
    UploadStartStatus,
)
from csob_ceb_bc.redaction import redact_contract
from csob_ceb_bc.rest.transfer import RestTransferClient
from csob_ceb_bc.soap.gateway import SoapGateway
from csob_ceb_bc.state.base import StateRepository

logger = get_logger("csob_ceb_bc.uploads")


class UploadManager:
    def __init__(
        self,
        *,
        contract_number: str,
        client_app_guid: str,
        soap: SoapGateway,
        rest: RestTransferClient,
        state: StateRepository,
        metrics: MetricsCollector | None = None,
    ) -> None:
        self._contract_number = contract_number
        self._client_app_guid = client_app_guid
        self._soap = soap
        self._rest = rest
        self._state = state
        self._metrics = metrics

    @staticmethod
    def compute_sha256(file: Path) -> str:
        h = hashlib.sha256()
        with open(file, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def upload_payment_batch(
        self,
        file: Path,
        metadata: UploadFile,
    ) -> UploadFinishResult | None:
        sha = self.compute_sha256(file)
        size = file.stat().st_size
        log_ctx = logger.bind(
            contract_redacted=redact_contract(self._contract_number),
            filename=metadata.filename,
            file_hash=sha,
        )

        # Idempotency check
        existing = self._state.get_attempt_id_by_hash(sha)
        if existing:
            log_ctx.info("upload_idempotent_skip", existing_attempt_id=existing)
            if self._metrics:
                self._metrics.inc("upload_idempotent_skips")
            return None

        attempt_id = str(uuid.uuid4())
        enriched = UploadFile(
            **metadata.model_dump(exclude={"hash", "size"}),
            hash=sha,
            size=size,
        )

        self._state.create_upload_attempt(
            attempt_id=attempt_id,
            filename=enriched.filename,
            file_hash=sha,
            size=size,
            file_format=enriched.format,
            mode=enriched.mode.value,
        )
        log_ctx.info("upload_start", attempt_id=attempt_id)

        start_results = self._soap.start_upload_file_list_v3(files=[enriched])
        if not start_results:
            return None
        start: UploadStartResult = start_results[0]
        log_ctx.info("upload_start_result", status=start.status.value, ticket_id=start.ticket_id)
        if self._metrics:
            self._metrics.inc("upload_start_calls")

        if start.status == UploadStartStatus.R:
            self._state.save_upload_finish_result(
                attempt_id=attempt_id, finish_status="R", ticket_id=start.ticket_id
            )
            log_ctx.info("upload_rejected_at_start", ticket_id=start.ticket_id)
            if self._metrics:
                self._metrics.inc("upload_rejected")
            return None

        if start.status == UploadStartStatus.U and start.url:
            if self._metrics:
                with timed(self._metrics, "upload_rest_latency_seconds"):
                    rest_result = self._rest.upload_multipart(
                        url=start.url,
                        file=file,
                        filename=enriched.filename,
                    )
            else:
                rest_result = self._rest.upload_multipart(
                    url=start.url,
                    file=file,
                    filename=enriched.filename,
                )
            self._state.save_upload_new_file_id(attempt_id, rest_result.new_file_id)
            log_ctx.info("upload_rest_complete", new_file_id=rest_result.new_file_id)
            if self._metrics:
                self._metrics.inc("upload_rest_success")

            finish_results = self._soap.finish_upload_file_list_v2(
                files=[(enriched.filename, sha, rest_result.new_file_id)]
            )
            if finish_results:
                finish = finish_results[0]
                self._state.save_upload_finish_result(
                    attempt_id=attempt_id,
                    finish_status=finish.status.value,
                    ticket_id=finish.ticket_id,
                )
                self._state.mark_idempotency_key(sha, attempt_id)
                log_ctx.info(
                    "upload_finish",
                    status=finish.status.value,
                    ticket_id=finish.ticket_id,
                )
                if self._metrics:
                    self._metrics.inc("upload_finish_calls")
                    if finish.status == UploadFinishStatus.I:
                        self._metrics.inc("upload_finish_import_started")
                    elif finish.status == UploadFinishStatus.R:
                        self._metrics.inc("upload_finish_rejected")
                return finish

        return None

    def resume_pending(self) -> list[UploadFinishResult]:
        """Resume uploads that completed REST transfer but not finish."""
        pending = self._state.get_pending_uploads()
        results: list[UploadFinishResult] = []
        for row in pending:
            attempt_id = row["attempt_id"]
            filename = row["filename"]
            file_hash = row["file_hash"]
            new_file_id = row["new_file_id"]
            finish_results = self._soap.finish_upload_file_list_v2(
                files=[(filename, file_hash, new_file_id)]
            )
            if finish_results:
                finish = finish_results[0]
                self._state.save_upload_finish_result(
                    attempt_id=attempt_id,
                    finish_status=finish.status.value,
                    ticket_id=finish.ticket_id,
                )
                results.append(finish)
                if self._metrics:
                    self._metrics.inc("upload_resume_success")
        if self._metrics:
            self._metrics.gauge("upload_pending_count", len(pending))
        return results
