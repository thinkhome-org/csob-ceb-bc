from __future__ import annotations

import asyncio
import hashlib
import uuid
from pathlib import Path

from csob_ceb_bc.errors import CsobBCHttpError, CsobBCSoapFault
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
from csob_ceb_bc.rest.async_transfer import AsyncRestTransferClient
from csob_ceb_bc.soap.async_gateway import AsyncSoapGateway
from csob_ceb_bc.state.base import StateRepository

logger = get_logger("csob_ceb_bc.uploads")


class UploadManager:
    def __init__(
        self,
        *,
        contract_number: str,
        client_app_guid: str,
        soap: AsyncSoapGateway,
        rest: AsyncRestTransferClient,
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

    async def upload_payment_batch(
        self,
        file: Path,
        metadata: UploadFile,
    ) -> UploadFinishResult | None:
        sha = await asyncio.to_thread(self.compute_sha256, file)
        size = await asyncio.to_thread(lambda: file.stat().st_size)
        log_ctx = logger.bind(
            contract_redacted=redact_contract(self._contract_number),
            filename=metadata.filename,
            file_hash=sha,
        )

        # Idempotency check
        existing = await asyncio.to_thread(self._state.get_attempt_id_by_hash, sha)
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

        await asyncio.to_thread(
            self._state.create_upload_attempt,
            attempt_id=attempt_id,
            filename=enriched.filename,
            file_hash=sha,
            size=size,
            file_format=enriched.format,
            mode=enriched.mode.value,
            local_path=str(file),
        )
        log_ctx.info("upload_start", attempt_id=attempt_id)

        start_results = await self._soap.start_upload_file_list_v3(files=[enriched])
        if not start_results:
            await asyncio.to_thread(
                self._state.save_upload_finish_result,
                attempt_id=attempt_id,
                finish_status="R",
                ticket_id=None,
            )
            log_ctx.warning("upload_start_empty_response")
            return None
        start: UploadStartResult = start_results[0]
        log_ctx.info("upload_start_result", status=start.status.value, ticket_id=start.ticket_id)
        if self._metrics:
            self._metrics.inc("upload_start_calls")

        if start.status == UploadStartStatus.R:
            await asyncio.to_thread(
                self._state.save_upload_finish_result,
                attempt_id=attempt_id,
                finish_status="R",
                ticket_id=start.ticket_id,
            )
            await asyncio.to_thread(self._state.mark_idempotency_key, sha, attempt_id)
            log_ctx.info("upload_rejected_at_start", ticket_id=start.ticket_id)
            if self._metrics:
                self._metrics.inc("upload_rejected")
            return None

        if start.status == UploadStartStatus.U and not start.url:
            await asyncio.to_thread(
                self._state.save_upload_finish_result,
                attempt_id=attempt_id,
                finish_status="R",
                ticket_id=start.ticket_id,
            )
            log_ctx.warning("upload_start_missing_url", ticket_id=start.ticket_id)
            return None

        if start.status == UploadStartStatus.U and start.url:
            await asyncio.to_thread(self._state.save_upload_start_url, attempt_id, start.url)
            if self._metrics:
                with timed(self._metrics, "upload_rest_latency_seconds"):
                    rest_result = await self._rest.upload_multipart(
                        url=start.url,
                        file=file,
                        filename=enriched.filename,
                    )
            else:
                rest_result = await self._rest.upload_multipart(
                    url=start.url,
                    file=file,
                    filename=enriched.filename,
                )
            await asyncio.to_thread(
                self._state.save_upload_new_file_id, attempt_id, rest_result.new_file_id
            )
            await asyncio.to_thread(self._state.mark_idempotency_key, sha, attempt_id)
            log_ctx.info("upload_rest_complete", new_file_id=rest_result.new_file_id)
            if self._metrics:
                self._metrics.inc("upload_rest_success")

            try:
                finish_results = await self._soap.finish_upload_file_list_v2(
                    files=[(enriched.filename, sha, rest_result.new_file_id)]
                )
            except CsobBCSoapFault as exc:
                if exc.permanent:
                    await asyncio.to_thread(
                        self._state.save_upload_finish_result,
                        attempt_id=attempt_id,
                        finish_status="R",
                        ticket_id=exc.ticket_id,
                    )
                    log_ctx.warning(
                        "upload_finish_permanent_fault",
                        error=exc.safe_message,
                        ticket_id=exc.ticket_id,
                    )
                    return None
                raise
            if finish_results:
                finish = finish_results[0]
                await asyncio.to_thread(
                    self._state.save_upload_finish_result,
                    attempt_id=attempt_id,
                    finish_status=finish.status.value,
                    ticket_id=finish.ticket_id,
                )
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

    async def resume_pending(self) -> list[UploadFinishResult]:
        """Resume uploads that completed REST transfer but not finish,
        or uploads that received a start URL but never completed REST."""
        pending = await asyncio.to_thread(self._state.get_pending_uploads)
        results: list[UploadFinishResult] = []
        for row in pending:
            attempt_id = row["attempt_id"]
            filename = row["filename"]
            file_hash = row["file_hash"]
            new_file_id = row.get("new_file_id")
            start_url = row.get("start_url")

            log_ctx = logger.bind(
                contract_redacted=redact_contract(self._contract_number),
                attempt_id=attempt_id,
                filename=filename,
            )

            if not new_file_id and start_url:
                # Crash between StartUploadFileList and REST upload
                log_ctx.info("upload_resume_rest", attempt_id=attempt_id)
                resume_file_path: Path | None = None
                raw_local = row.get("local_path")
                if raw_local:
                    resume_file_path = Path(raw_local)
                    if not resume_file_path.exists():
                        log_ctx.warning(
                            "upload_resume_local_path_missing",
                            local_path=str(resume_file_path),
                        )
                        resume_file_path = None
                if resume_file_path is None:
                    resume_file_path = Path(filename)
                try:
                    rest_result = await self._rest.upload_multipart(
                        url=start_url,
                        file=resume_file_path,
                        filename=filename,
                    )
                    await asyncio.to_thread(
                        self._state.save_upload_new_file_id,
                        attempt_id,
                        rest_result.new_file_id,
                    )
                    await asyncio.to_thread(self._state.mark_idempotency_key, file_hash, attempt_id)
                    new_file_id = rest_result.new_file_id
                except CsobBCHttpError as exc:
                    if exc.permanent:
                        await asyncio.to_thread(
                            self._state.save_upload_finish_result,
                            attempt_id=attempt_id,
                            finish_status="R",
                            ticket_id=None,
                        )
                        log_ctx.warning(
                            "upload_resume_permanent_failure",
                            error=exc.safe_message,
                        )
                        continue
                    log_ctx.warning("upload_resume_rest_failed", error=str(exc))
                    continue
                except Exception as exc:
                    log_ctx.warning("upload_resume_rest_failed", error=str(exc))
                    continue

            if new_file_id:
                try:
                    finish_results = await self._soap.finish_upload_file_list_v2(
                        files=[(filename, file_hash, new_file_id)]
                    )
                except CsobBCSoapFault as exc:
                    if exc.permanent:
                        await asyncio.to_thread(
                            self._state.save_upload_finish_result,
                            attempt_id=attempt_id,
                            finish_status="R",
                            ticket_id=exc.ticket_id,
                        )
                        log_ctx.warning(
                            "upload_resume_finish_permanent_fault",
                            error=exc.safe_message,
                        )
                        continue
                    raise
                if finish_results:
                    finish = finish_results[0]
                    await asyncio.to_thread(
                        self._state.save_upload_finish_result,
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
