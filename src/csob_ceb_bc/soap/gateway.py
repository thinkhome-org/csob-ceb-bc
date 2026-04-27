from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import zeep
from zeep.exceptions import Fault

from csob_ceb_bc.certificates.store import CertificateStore
from csob_ceb_bc.config import ConnectorConfig, Environment
from csob_ceb_bc.errors import CsobBCProtocolError, CsobBCRateLimitError
from csob_ceb_bc.models import (
    DownloadFile,
    DownloadFileStatus,
    DownloadFileType,
    DownloadFilter,
    UploadFile,
    UploadFinishResult,
    UploadFinishStatus,
    UploadStartResult,
    UploadStartStatus,
)
from csob_ceb_bc.rate_limit import TokenBucketRateLimiter
from csob_ceb_bc.retry import retry_soap
from csob_ceb_bc.soap.faults import map_soap_fault


class DownloadListResult:
    def __init__(self, query_timestamp: datetime, files: list[DownloadFile]):
        self.query_timestamp = query_timestamp
        self.files = files


class SoapGateway:
    """SOAP orchestration layer for ČSOB BC."""

    PROD_URL = "https://ceb-bc.csob.cz/cebbc/api"
    DEMO_URL = "https://testceb-bc.csob.cz/cebbc/api"

    def __init__(
        self,
        config: ConnectorConfig,
        wsdl_path: str | None = None,
        rate_limiter: TokenBucketRateLimiter | None = None,
        cert_store: CertificateStore | None = None,
    ) -> None:
        self._config = config
        self._endpoint = self.DEMO_URL if config.environment == Environment.DEMO else self.PROD_URL
        self._wsdl_path = wsdl_path or self._endpoint + "?wsdl"
        self._client = zeep.Client(self._wsdl_path)  # type: ignore[no-untyped-call]
        self._rate_limiter = rate_limiter
        self._cert_store = cert_store
        self._setup_transport()

    def _check_rate_limit(self) -> None:
        if self._rate_limiter is not None and not self._rate_limiter.acquire():
            raise CsobBCRateLimitError(
                "SOAP rate limit exceeded",
                operation="soap",
                safe_message="Rate limit exceeded",
            )

    def _setup_transport(self) -> None:
        # zeep uses requests under the hood; configure mTLS via transport session
        import requests
        from requests.adapters import HTTPAdapter

        session = requests.Session()
        cert = self._config.certificate
        if self._cert_store is not None:
            session.cert = (str(self._cert_store.cert_path), str(self._cert_store.key_path))
            if cert.ca_bundle:
                session.verify = str(cert.ca_bundle)
        elif cert.cert_file and cert.key_file:
            session.cert = (str(cert.cert_file), str(cert.key_file))
            if cert.ca_bundle:
                session.verify = str(cert.ca_bundle)

        adapter = HTTPAdapter()
        session.mount("https://", adapter)
        self._client.transport.session = session

    def _extract_ticket_id(self, detail: Any) -> str | None:
        if isinstance(detail, dict):
            return detail.get("TicketId") or detail.get("ticketId")
        return None

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        # Handle xsd:dateTime format; fallback to fromisoformat
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _handle_soap_fault(self, fault: Fault) -> None:
        ticket_id = self._extract_ticket_id(fault.detail)
        fault_code = None
        fault_string = str(fault)
        if isinstance(fault.detail, dict):
            fault_code = fault.detail.get("FaultCode") or fault.detail.get("faultcode")
            fault_string = (
                fault.detail.get("FaultString") or fault.detail.get("faultstring") or fault_string
            )
        raise map_soap_fault(
            fault_code=fault_code,
            fault_string=fault_string,
            ticket_id=ticket_id,
        ) from fault

    @retry_soap(max_attempts=3)
    def get_download_file_list_v4(
        self,
        prev_query_timestamp: datetime | None = None,
        filter: DownloadFilter | None = None,
    ) -> DownloadListResult:
        self._check_rate_limit()
        request: dict[str, Any] = {"ContractNumber": self._config.contract_number}
        if prev_query_timestamp is not None:
            request["PrevQueryTimestamp"] = prev_query_timestamp.isoformat()
        if filter:
            filter_dict: dict[str, Any] = {}
            if filter.file_types:
                filter_dict["FileTypes"] = {"FileType": [ft.value for ft in filter.file_types]}
            if filter.file_formats:
                filter_dict["FileFormats"] = {"FileFormat": filter.file_formats}
            if filter.filename:
                filter_dict["FileName"] = filter.filename
            if filter.created_after is not None:
                filter_dict["CreatedAfter"] = filter.created_after.isoformat()
            if filter.created_before is not None:
                filter_dict["CreatedBefore"] = filter.created_before.isoformat()
            if filter.client_app_guid:
                filter_dict["ClientAppGuid"] = filter.client_app_guid
            if filter_dict:
                request["Filter"] = filter_dict

        try:
            response = self._client.service.GetDownloadFileList(**request)
        except Fault as fault:
            self._handle_soap_fault(fault)

        qt = self._parse_datetime(response.get("QueryTimestamp"))
        if qt is None:
            qt = datetime.now(UTC)

        files: list[DownloadFile] = []
        file_list = response.get("FileList")
        if file_list:
            file_details = file_list.get("FileDetail")
            if file_details is not None and not isinstance(file_details, list):
                file_details = [file_details]
            for fd in file_details or []:
                cdt = self._parse_datetime(fd.get("CreationDateTime"))
                if cdt is None:
                    raise CsobBCProtocolError(
                        f"GetDownloadFileList response has unparseable "
                        f"CreationDateTime: {fd.get('CreationDateTime')!r}",
                        operation="GetDownloadFileList",
                    )
                files.append(
                    DownloadFile(
                        filename=fd.get("Filename", ""),
                        type=DownloadFileType(fd.get("Type", "VYPIS")),
                        format=fd.get("Format"),
                        creation_date_time=cdt,
                        size=fd.get("Size"),
                        status=DownloadFileStatus(fd.get("Status", "R")),
                        url=fd.get("Url"),
                        upload_file_hash=fd.get("UploadFileHash"),
                        ticket_id=fd.get("TicketId"),
                    )
                )

        result = DownloadListResult(query_timestamp=qt, files=files)
        result.ticket_id = self._extract_ticket_id(response)  # type: ignore[attr-defined]
        return result

    @retry_soap(max_attempts=3)
    def start_upload_file_list_v3(self, files: list[UploadFile]) -> list[UploadStartResult]:
        self._check_rate_limit()
        request_files = [
            {
                "Filename": f.filename,
                "Hash": f.hash,
                "Size": f.size,
                "Format": f.format,
                "Separator": f.separator,
                "Mode": f.mode.value,
                "SkipCheckDuplicates": f.skip_check_duplicates,
            }
            for f in files
        ]
        request = {
            "ContractNumber": self._config.contract_number,
            "ClientAppGuid": self._config.client_app_guid,
            "Files": {"File": request_files},
        }

        try:
            response = self._client.service.StartUploadFileList(**request)
        except Fault as fault:
            self._handle_soap_fault(fault)

        results: list[UploadStartResult] = []
        file_list = response.get("FileList", {})
        statuses = file_list.get("FileUrl") if file_list else None
        if statuses is None:
            statuses = response.get("FileStatus", [])
        if statuses is not None and not isinstance(statuses, list):
            statuses = [statuses]
        for fs in statuses or []:
            results.append(
                UploadStartResult(
                    filename=fs.get("Filename", ""),
                    status=UploadStartStatus(fs.get("Status", "R")),
                    hash=fs.get("Hash"),
                    url=fs.get("Url"),
                    ticket_id=fs.get("TicketId"),
                )
            )
        return results

    @retry_soap(max_attempts=3)
    def finish_upload_file_list_v2(
        self,
        files: list[tuple[str, str, str]],  # (filename, hash, new_file_id)
    ) -> list[UploadFinishResult]:
        self._check_rate_limit()
        request_files = [{"Filename": fn, "Hash": h, "NewFileId": nfid} for fn, h, nfid in files]
        request = {
            "ContractNumber": self._config.contract_number,
            "ClientAppGuid": self._config.client_app_guid,
            "Files": {"File": request_files},
        }

        try:
            response = self._client.service.FinishUploadFileList(**request)
        except Fault as fault:
            self._handle_soap_fault(fault)

        results: list[UploadFinishResult] = []
        file_list = response.get("FileList", {})
        statuses = file_list.get("FileStatus") if file_list else []
        if statuses is not None and not isinstance(statuses, list):
            statuses = [statuses]
        for fs in statuses or []:
            results.append(
                UploadFinishResult(
                    filename=fs.get("Filename", ""),
                    hash=fs.get("Hash", ""),
                    status=UploadFinishStatus(fs.get("Status", "R")),
                    ticket_id=fs.get("TicketId"),
                )
            )
        return results
