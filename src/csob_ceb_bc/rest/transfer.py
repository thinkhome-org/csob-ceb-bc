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
        try:
            with (
                self._client() as client,
                client.stream("GET", url, timeout=self._timeout) as response,
            ):
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
                self._raise_for_status(response.status_code, "download")
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
            raise CsobBCHttpError(
                f"Download timeout: {exc.__class__.__name__}",
                operation="download",
                permanent=False,
                retryable=True,
                safe_message="Download timeout",
            ) from exc
        except Exception:
            if part.exists():
                part.unlink()
            raise
        raise RuntimeError("unreachable")  # pragma: no cover

    @retry_rest(max_attempts=3)
    def upload_multipart(self, url: str, file: Path, filename: str) -> RestUploadResult:
        try:
            with self._client() as client, open(file, "rb") as f:
                files = {
                    "fileupload": (filename, f, "application/octet-stream"),
                }
                response = client.post(url, files=files, timeout=self._timeout)
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
            raise CsobBCHttpError(
                f"Upload timeout: {exc.__class__.__name__}",
                operation="upload",
                permanent=False,
                retryable=True,
                safe_message="Upload timeout",
            ) from exc

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

        self._raise_for_json_status(result.status, "upload")
        return result

    def _raise_for_status(self, status: int, operation: str) -> None:
        if operation == "download":
            permanent_codes = {400, 401, 404}
            retryable_codes = {500, 503}
        else:  # upload
            permanent_codes = {400, 401, 403}
            retryable_codes = {408, 429, 500, 502, 503, 504}

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
        )  # pragma: no cover

    def _raise_for_json_status(self, status: str, operation: str) -> None:
        json_permanent = {"450", "451", "452", "453", "454"}
        json_retryable = {"455", "456"}

        if status in json_permanent:
            raise CsobBCHttpError(
                f"REST upload status {status} permanent error",
                operation=operation,
                permanent=True,
                retryable=False,
                safe_message=f"Upload status {status}",
            )
        if status in json_retryable:
            raise CsobBCHttpError(
                f"REST upload status {status} retryable error",
                operation=operation,
                permanent=False,
                retryable=True,
                safe_message=f"Upload status {status}",
            )
        if status != "201":
            raise CsobBCHttpError(
                f"REST upload status {status} unexpected error",
                operation=operation,
                safe_message=f"Upload status {status}",
            )
