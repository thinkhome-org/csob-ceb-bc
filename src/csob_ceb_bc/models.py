from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DownloadFileType(str, Enum):
    VYPIS = "VYPIS"
    AVIZO = "AVIZO"
    KURZY = "KURZY"
    IMPPROT = "IMPPROT"


class DownloadFileStatus(str, Enum):
    R = "R"
    D = "D"
    F = "F"


class UploadMode(str, Enum):
    IncludeIncorrect = "IncludeIncorrect"
    OnlyCorrect = "OnlyCorrect"
    AllOrNothing = "AllOrNothing"
    SignedAllOrNothing = "SignedAllOrNothing"


class UploadStartStatus(str, Enum):
    R = "R"
    U = "U"


class UploadFinishStatus(str, Enum):
    R = "R"
    I = "I"


class DownloadFilter(BaseModel):
    """Filter for GetDownloadFileList v4."""

    file_types: list[DownloadFileType] | None = None

    model_config = {"frozen": True}


class DownloadFile(BaseModel):
    """File detail from SOAP response."""

    filename: str
    type: DownloadFileType
    format: str | None = None
    creation_date_time: datetime
    size: int | None = None
    status: DownloadFileStatus
    url: str | None = None
    upload_file_hash: str | None = None

    model_config = {"frozen": True}


class UploadFile(BaseModel):
    """Upload metadata for StartUploadFileList v3."""

    filename: str = Field(..., max_length=50)
    hash: str | None = None
    size: int | None = None
    format: str
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
        except ValueError:
            raise ValueError("hash must be valid hex")
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
    url: str | None = None
    ticket_id: str | None = None

    model_config = {"frozen": True}


class RestUploadResult(BaseModel):
    """Parsed JSON response from REST upload POST."""

    status: str = Field(..., alias="Status")
    ext_file_url: str = Field(..., alias="ExtFileUrl")
    new_file_id: str = Field(..., alias="NewFileId")

    model_config = {"frozen": True, "populate_by_name": True}


class UploadFinishResult(BaseModel):
    """Result of FinishUploadFileList v2 for a single file."""

    filename: str
    hash: str
    status: UploadFinishStatus
    ticket_id: str | None = None

    model_config = {"frozen": True}


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
