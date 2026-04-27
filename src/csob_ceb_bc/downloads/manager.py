from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from csob_ceb_bc.models import DownloadFile, DownloadFileStatus, DownloadFilter
from csob_ceb_bc.rest.transfer import RestTransferClient
from csob_ceb_bc.soap.gateway import SoapGateway
from csob_ceb_bc.state.base import StateRepository


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
    ) -> None:
        self._contract_number = contract_number
        self._client_app_guid = client_app_guid
        self._cert_fingerprint = cert_fingerprint
        self._environment = environment
        self._soap = soap
        self._rest = rest
        self._state = state

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
        result = self._soap.get_download_file_list_v4(
            prev_query_timestamp=prev,
            filter=filter,
        )

        downloaded: list[DownloadFile] = []
        has_unresolved = False

        for file in result.files:
            if file.status == DownloadFileStatus.R or file.url is None:
                has_unresolved = True
                continue
            if file.status == DownloadFileStatus.F:
                # permanent failure — log and skip
                continue
            if file.status == DownloadFileStatus.D and file.url:
                local_path = target_dir / file.filename
                self._rest.download_to_file(file.url, local_path)
                downloaded.append(file)

        if not has_unresolved and downloaded:
            self._state.set_profile_cursor(key, result.query_timestamp)
        elif not has_unresolved and not downloaded:
            # no files at all, safe to advance cursor
            self._state.set_profile_cursor(key, result.query_timestamp)

        return downloaded
