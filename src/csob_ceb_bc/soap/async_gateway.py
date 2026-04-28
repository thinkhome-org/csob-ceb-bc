from __future__ import annotations

import asyncio
from datetime import datetime

from csob_ceb_bc.models import DownloadFilter, UploadFile, UploadFinishResult, UploadStartResult
from csob_ceb_bc.soap.gateway import DownloadListResult, SoapGateway


class AsyncSoapGateway:
    """Async boundary over the sync zeep-based SOAP gateway."""

    def __init__(self, gateway: SoapGateway) -> None:
        self._gateway = gateway
        self._lock = asyncio.Lock()

    async def get_download_file_list_v4(
        self,
        prev_query_timestamp: datetime | None = None,
        filter: DownloadFilter | None = None,
    ) -> DownloadListResult:
        async with self._lock:
            return await asyncio.to_thread(
                self._gateway.get_download_file_list_v4,
                prev_query_timestamp,
                filter,
            )

    async def start_upload_file_list_v3(self, files: list[UploadFile]) -> list[UploadStartResult]:
        async with self._lock:
            return await asyncio.to_thread(self._gateway.start_upload_file_list_v3, files)

    async def finish_upload_file_list_v2(
        self,
        files: list[tuple[str, str, str]],
    ) -> list[UploadFinishResult]:
        async with self._lock:
            return await asyncio.to_thread(self._gateway.finish_upload_file_list_v2, files)
