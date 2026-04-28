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
        self._rate_limiter = rate_limiter
        self._cert_store = cert_store
        self._transport = self._create_transport()
        self._client = zeep.Client(self._wsdl_path, transport=self._transport)  # type: ignore[no-untyped-call]

    def _check_rate_limit(self) -> None:
        if self._rate_limiter is not None and not self._rate_limiter.acquire():
            raise CsobBCRateLimitError(
                "SOAP rate limit exceeded",
                operation="soap",
                safe_message="Rate limit exceeded",
            )

    def _create_transport(self) -> zeep.Transport:
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
        return zeep.Transport(session=session)  # type: ignore[no-untyped-call]

    @staticmethod
    def _get_value(obj: Any, key: str, default: Any = None) -> Any:
        """Extract value from dict or zeep object."""
        if obj is None:
            return default
        if hasattr(obj, key):
            return getattr(obj, key)
        if hasattr(obj, "get"):
            return obj.get(key, default)
        return default

    def _extract_ticket_id(self, detail: Any) -> str | None:
        if isinstance(detail, dict):
            result: str | None = (
                self._get_value(detail, "TicketId")
                or self._get_value(detail, "ticketId")
            )
            return result
        return None

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        # zeep may already return a datetime object for xs:dateTime fields
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
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
            fault_code = self._get_value(
                fault.detail, "FaultCode"
            ) or self._get_value(fault.detail, "faultcode")
            fault_string = (
                self._get_value(fault.detail, "FaultString")
                or self._get_value(fault.detail, "faultstring")
                or fault_string
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
            response = self._client.service.GetDownloadFileList_v2(**request)
        except Fault as fault:
            self._handle_soap_fault(fault)

        qt = self._parse_datetime(self._get_value(response, "QueryTimestamp"))
        if qt is None:
            qt = datetime.now(UTC)

        files: list[DownloadFile] = []
        file_list = self._get_value(response, "FileList")
        if file_list:
            file_details = self._get_value(file_list, "FileDetail")
            if file_details is not None and not isinstance(file_details, list):
                file_details = [file_details]
            for fd in file_details or []:
                cdt = self._parse_datetime(self._get_value(fd, "CreationDateTime"))
                if cdt is None:
                    raise CsobBCProtocolError(
                        f"GetDownloadFileList response has unparseable "
                        f"CreationDateTime: {self._get_value(fd, 'CreationDateTime')!r}",
                        operation="GetDownloadFileList",
                    )
                files.append(
                    DownloadFile(
                        filename=self._get_value(fd, "Filename", ""),
                        type=DownloadFileType(self._get_value(fd, "Type", "VYPIS")),
                        format=self._get_value(fd, "Format"),
                        creation_date_time=cdt,
                        size=self._get_value(fd, "Size"),
                        status=DownloadFileStatus(self._get_value(fd, "Status", "R")),
                        url=self._get_value(fd, "Url"),
                        upload_file_hash=self._get_value(fd, "UploadFileHash"),
                        ticket_id=self._get_value(fd, "TicketId"),
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
            }
            for f in files
        ]
        request = {
            "ContractNumber": self._config.contract_number,
            "ClientAppGuid": self._config.client_app_guid,
            "FileList": {"ImportFileDetail": request_files},
        }

        try:
            response = self._client.service.StartUploadFileList_v1(**request)
        except Fault as fault:
            self._handle_soap_fault(fault)

        results: list[UploadStartResult] = []
        file_list = self._get_value(response, "FileList", {})
        statuses = self._get_value(file_list, "FileUrl") if file_list else None
        if statuses is None:
            statuses = self._get_value(response, "FileStatus", [])
        if statuses is not None and not isinstance(statuses, list):
            statuses = [statuses]
        for fs in statuses or []:
            results.append(
                UploadStartResult(
                    filename=self._get_value(fs, "Filename", ""),
                    status=UploadStartStatus(self._get_value(fs, "Status", "R")),
                    hash=self._get_value(fs, "Hash"),
                    url=self._get_value(fs, "Url"),
                    ticket_id=self._get_value(fs, "TicketId"),
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
            "FileList": {"FileId": request_files},
        }

        try:
            response = self._client.service.FinishUploadFileList_v1(**request)
        except Fault as fault:
            self._handle_soap_fault(fault)

        results: list[UploadFinishResult] = []
        file_list = self._get_value(response, "FileList", {})
        statuses = self._get_value(file_list, "FileStatus") if file_list else []
        if statuses is not None and not isinstance(statuses, list):
            statuses = [statuses]
        for fs in statuses or []:
            results.append(
                UploadFinishResult(
                    filename=self._get_value(fs, "Filename", ""),
                    hash=self._get_value(fs, "Hash", ""),
                    status=UploadFinishStatus(self._get_value(fs, "Status", "R")),
                    ticket_id=self._get_value(fs, "TicketId"),
                )
            )
        return results
