from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

from csob_ceb_bc.certificates.store import CertificateStore
from csob_ceb_bc.errors import CsobBCHttpError, CsobBCProtocolError
from csob_ceb_bc.models import HttpTransferResult, RestUploadResult
from csob_ceb_bc.retry import retry_rest


class RestTransferClient:
    """Streaming REST download and multipart upload."""

    def __init__(
        self,
        cert_store: CertificateStore,
        timeout: httpx.Timeout | None = None,
        verify: bool | str = True,
    ) -> None:
        self._cert_store = cert_store
        self._timeout = timeout or httpx.Timeout(120.0, connect=10.0, read=120.0, write=120.0)
        self._verify = verify

    def _client(self) -> httpx.Client:
        return self._cert_store.build_httpx_client(verify=self._verify)

    @retry_rest(max_attempts=3)
    def download_to_file(self, url: str, target: Path) -> HttpTransferResult:
        part = target.with_suffix(target.suffix + ".part")
        start = time.monotonic()
        with self._client() as client:
            with client.stream("GET", url, timeout=self._timeout) as response:
                if response.status_code == 200:
                    with open(part, "wb") as f:
                        for chunk in response.iter_bytes():
                            f.write(chunk)
                    part.rename(target)
                    duration = time.monotonic() - start
                    return HttpTransferResult(
                        http_status=response.status_code,
                        bytes_transferred=target.stat().st_size if target.exists() else 0,
                        duration_seconds=duration,
                        headers=dict(response.headers),
                    )
                else:
                    self._raise_for_status(response.status_code, "download")
        # unreachable
        raise RuntimeError("unreachable")

    @retry_rest(max_attempts=3)
    def upload_multipart(self, url: str, file: Path, filename: str) -> RestUploadResult:
        start = time.monotonic()
        with self._client() as client:
            with open(file, "rb") as f:
                files = {
                    "fileupload": (filename, f, "application/octet-stream"),
                }
                response = client.post(url, files=files, timeout=self._timeout)

        if response.status_code not in (200, 201):
            self._raise_for_status(response.status_code, "upload")

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise CsobBCProtocolError(
                "REST upload returned non-JSON",
                operation="upload",
                safe_message="Malformed REST upload response",
            ) from exc

        try:
            result = RestUploadResult.model_validate(data)
        except Exception as exc:
            raise CsobBCProtocolError(
                "REST upload JSON does not match expected schema",
                operation="upload",
                safe_message="Malformed REST upload JSON schema",
            ) from exc

        return result

    def _raise_for_status(self, status: int, operation: str) -> None:
        permanent_codes = {400, 401, 403, 404, 450, 451, 452, 453, 454}
        retryable_codes = {408, 500, 502, 503, 504, 455, 456}

        if status in permanent_codes:
            raise CsobBCHttpError(
                f"HTTP {status} permanent error",
                operation=operation,
                permanent=True,
                retryable=False,
                safe_message=f"HTTP {status}",
            )
        if status in retryable_codes:
            raise CsobBCHttpError(
                f"HTTP {status} retryable error",
                operation=operation,
                permanent=False,
                retryable=True,
                safe_message=f"HTTP {status}",
            )
        raise CsobBCHttpError(
            f"HTTP {status} unexpected error",
            operation=operation,
            safe_message=f"HTTP {status}",
        )
