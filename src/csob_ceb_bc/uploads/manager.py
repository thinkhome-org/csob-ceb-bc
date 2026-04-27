from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from csob_ceb_bc.models import (
    UploadFile,
    UploadFinishResult,
    UploadFinishStatus,
    UploadStartResult,
    UploadStartStatus,
)
from csob_ceb_bc.rest.transfer import RestTransferClient
from csob_ceb_bc.soap.gateway import SoapGateway
from csob_ceb_bc.state.base import StateRepository


class UploadManager:
    def __init__(
        self,
        *,
        contract_number: str,
        client_app_guid: str,
        soap: SoapGateway,
        rest: RestTransferClient,
        state: StateRepository,
    ) -> None:
        self._contract_number = contract_number
        self._client_app_guid = client_app_guid
        self._soap = soap
        self._rest = rest
        self._state = state

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

        # Idempotency check
        existing = self._state.get_attempt_id_by_hash(sha)
        if existing:
            # Already attempted; do not blindly re-upload
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

        start_results = self._soap.start_upload_file_list_v3(files=[enriched])
        if not start_results:
            return None
        start: UploadStartResult = start_results[0]

        if start.status == UploadStartStatus.R:
            self._state.save_upload_finish_result(
                attempt_id=attempt_id, finish_status="R", ticket_id=start.ticket_id
            )
            return None

        if start.status == UploadStartStatus.U and start.url:
            rest_result = self._rest.upload_multipart(
                url=start.url,
                file=file,
                filename=enriched.filename,
            )
            self._state.save_upload_new_file_id(attempt_id, rest_result.new_file_id)

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
                return finish

        return None
