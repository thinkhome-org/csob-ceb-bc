from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DownloadFileType(StrEnum):
    VYPIS = "VYPIS"
    AVIZO = "AVIZO"
    KURZY = "KURZY"
    IMPPROT = "IMPPROT"


class DownloadFileFormat(StrEnum):
    """Allowed file formats for GetDownloadFileList filter.

    Per manual §3.2.1.1:
    – Statements (VYPIS): PDF, TXT, XML, BBGPC, BBMT940, BBTXT, BBBBF, SEPAXML
    – Avíza (AVIZO): MT942, BBF, CAMT052
    – Exchange rates (KURZY): format is ignored by the service
    """

    PDF = "PDF"
    TXT = "TXT"
    XML = "XML"
    BBGPC = "BBGPC"
    BBMT940 = "BBMT940"
    BBTXT = "BBTXT"
    BBBBF = "BBBBF"
    SEPAXML = "SEPAXML"
    MT942 = "MT942"
    BBF = "BBF"
    CAMT052 = "CAMT052"


class DownloadFileStatus(StrEnum):
    R = "R"
    D = "D"
    F = "F"


class UploadMode(StrEnum):
    IncludeIncorrect = "IncludeIncorrect"
    OnlyCorrect = "OnlyCorrect"
    AllOrNothing = "AllOrNothing"
    SignedAllOrNothing = "SignedAllOrNothing"


class UploadStartStatus(StrEnum):
    R = "R"
    U = "U"


class UploadFinishStatus(StrEnum):
    R = "R"
    I = "I"  # noqa: E741


class DownloadFilter(BaseModel):
    """Filter for GetDownloadFileList v4."""

    file_types: list[DownloadFileType] | None = None
    file_formats: list[DownloadFileFormat] | None = None
    filename: str | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    client_app_guid: str | None = None

    model_config = {"frozen": True}

    @field_validator("created_after", "created_before")
    @classmethod
    def _datetime_must_be_tz_aware(cls, v: datetime | None) -> datetime | None:
        """Manual §3.2.1.1 requires xsd:dateTime format YYYY-MM-DDTHH:MM:SS+ZZ:ZZ."""
        if v is None:
            return v
        if v.tzinfo is None:
            raise ValueError("datetime must be timezone-aware (e.g. datetime.now(UTC))")
        return v

    @field_validator("client_app_guid")
    @classmethod
    def _guid_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not re.fullmatch(
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
            v,
        ):
            raise ValueError(
                "client_app_guid must be a UUID in format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )
        return v


class DownloadFile(BaseModel):
    """File detail from SOAP response."""

    filename: str
    type: DownloadFileType
    format: DownloadFileFormat | None = None
    creation_date_time: datetime
    size: int | None = None
    status: DownloadFileStatus
    url: str | None = None
    upload_file_hash: str | None = Field(
        default=None,
        description=(
            "SHA256 hash of the original uploaded file. "
            "Present only for IMPPROT (import protocol) files."
        ),
    )
    ticket_id: str | None = None

    model_config = {"frozen": True}


class UploadFile(BaseModel):
    """Upload metadata for StartUploadFileList v3."""

    filename: str = Field(..., max_length=50)
    hash: str | None = None
    size: int | None = None
    format: str = Field(
        ...,
        pattern=(
            r"^(ABO|DUZ|MC TPS|MC ZPS|TXT TPS|TXT ZPS|XLS TPS|XLS ZPS"
            r"|XLSX TPS|XLSX ZPS|MT101|XML SEPA|XML TPS|XML ZPS)$"
        ),
    )
    separator: str | None = None
    mode: UploadMode
    skip_check_duplicates: bool = False

    @field_validator("filename")
    @classmethod
    def _filename_max_length(cls, v: str) -> str:
        if len(v) > 50:
            raise ValueError("filename must be at most 50 characters")
        return v

    @field_validator("separator")
    @classmethod
    def _separator_allowed(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"|", "/", ":", "::", ";", ";;"}
        if v not in allowed:
            raise ValueError(f"separator must be one of {allowed}")
        return v

    @field_validator("hash")
    @classmethod
    def _hash_must_be_sha256(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) != 64:
            raise ValueError("hash must be 64 hex characters (SHA256)")
        try:
            int(v, 16)
        except ValueError as exc:
            raise ValueError("hash must be valid hex") from exc
        return v

    @field_validator("skip_check_duplicates", mode="before")
    @classmethod
    def _signed_no_skip(cls, v: Any, info: Any) -> Any:
        data = info.data
        mode = data.get("mode")
        if mode == UploadMode.SignedAllOrNothing and v is True:
            raise ValueError("skip_check_duplicates cannot be True for SignedAllOrNothing")
        return v


class UploadStartResult(BaseModel):
    """Result of StartUploadFileList v3 for a single file."""

    filename: str
    status: UploadStartStatus
    hash: str | None = None
    url: str | None = None
    ticket_id: str | None = None

    model_config = {"frozen": True}

    @field_validator("hash")
    @classmethod
    def _hash_must_be_sha256(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) != 64:
            raise ValueError("hash must be 64 hex characters (SHA256)")
        try:
            int(v, 16)
        except ValueError as exc:
            raise ValueError("hash must be valid hex") from exc
        return v


class RestUploadResult(BaseModel):
    """Parsed JSON response from REST upload POST."""

    status: str = Field(..., alias="Status")
    ext_file_url: str = Field(..., alias="ExtFileUrl")
    new_file_id: str = Field(..., alias="NewFileId")

    model_config = {"frozen": True, "populate_by_name": True}


class DownloadBatchResult(BaseModel):
    """Result of a download batch operation."""

    downloaded: list[DownloadFile] = Field(default_factory=list)
    pending: list[DownloadFile] = Field(default_factory=list)
    failed: list[DownloadFile] = Field(default_factory=list)
    cursor_advanced: bool = False
    query_timestamp: datetime | None = None

    model_config = {"frozen": True}

    def __len__(self) -> int:
        """Return number of downloaded files for backward compatibility."""
        return len(self.downloaded)

    @property
    def has_pending_files(self) -> bool:
        """True if any files are still being prepared (status R without URL)."""
        return len(self.pending) > 0


class UploadFinishResult(BaseModel):
    """Result of FinishUploadFileList v2 for a single file."""

    filename: str
    hash: str
    status: UploadFinishStatus
    ticket_id: str | None = None

    model_config = {"frozen": True}

    @field_validator("hash")
    @classmethod
    def _hash_must_be_sha256(cls, v: str) -> str:
        if len(v) != 64:
            raise ValueError("hash must be 64 hex characters (SHA256)")
        try:
            int(v, 16)
        except ValueError as exc:
            raise ValueError("hash must be valid hex") from exc
        return v


class ImportProtocolRecord(BaseModel):
    """Tracked import protocol state."""

    new_file_id: str
    upload_hash: str
    filename: str
    client_app_guid: str
    local_path: str | None = None
    downloaded_at: datetime | None = None

    model_config = {"frozen": True}


class SoapFaultInfo(BaseModel):
    """Structured SOAP fault data."""

    fault_code: str | None = None
    fault_string: str | None = None
    ticket_id: str | None = None

    model_config = {"frozen": True}


class HttpTransferResult(BaseModel):
    """Result of a single REST transfer."""

    http_status: int
    bytes_transferred: int
    duration_seconds: float
    headers: dict[str, str] | None = None

    model_config = {"frozen": True}


class StateRecord(BaseModel):
    """Generic state record abstraction."""

    profile_key: str
    last_query_timestamp: datetime | None = None

    model_config = {"frozen": True}
