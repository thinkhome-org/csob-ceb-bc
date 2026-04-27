from __future__ import annotations

from pathlib import Path

from csob_ceb_bc.metrics import MetricsCollector, timed
from csob_ceb_bc.models import DownloadFile, DownloadFileStatus, DownloadFileType, DownloadFilter
from csob_ceb_bc.rest.transfer import RestTransferClient
from csob_ceb_bc.soap.gateway import SoapGateway
from csob_ceb_bc.state.base import StateRepository


class ImportProtocolManager:
    def __init__(
        self,
        *,
        client_app_guid: str,
        soap: SoapGateway,
        rest: RestTransferClient,
        state: StateRepository,
        metrics: MetricsCollector | None = None,
    ) -> None:
        self._client_app_guid = client_app_guid
        self._soap = soap
        self._rest = rest
        self._state = state
        self._metrics = metrics

    def poll_import_protocols(self, target_dir: Path) -> list[DownloadFile]:
        target_dir.mkdir(parents=True, exist_ok=True)
        result = self._soap.get_download_file_list_v4(
            filter=DownloadFilter(file_types=[DownloadFileType.IMPPROT]),
        )
        if self._metrics:
            self._metrics.inc("import_protocol_soap_calls")
            self._metrics.gauge("import_protocol_file_count", len(result.files))

        downloaded: list[DownloadFile] = []
        for file in result.files:
            if file.status != DownloadFileStatus.D or not file.url:
                continue
            if file.upload_file_hash:
                local_path = target_dir / file.filename
                if self._metrics:
                    with timed(self._metrics, "import_protocol_download_latency_seconds"):
                        self._rest.download_to_file(file.url, local_path)
                else:
                    self._rest.download_to_file(file.url, local_path)
                downloaded.append(file)
                if self._metrics:
                    self._metrics.inc("import_protocol_download_success")
        return downloaded
