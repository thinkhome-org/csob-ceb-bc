"""Zeep contract tests against local WSDL/XSD.

These tests prove that the SDK can serialize requests against the real
local WSDL definitions without ValidationError at build-time.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import zeep

from csob_ceb_bc.models import DownloadFileFormat, DownloadFileType, DownloadFilter

WSDL_PATH = Path(__file__).parent.parent.parent / "wsdl" / "CEBBCWS.wsdl"


@pytest.fixture
def zeep_client() -> zeep.Client:
    return zeep.Client(str(WSDL_PATH))  # type: ignore[no-untyped-call]


def test_get_download_file_list_v4_serializes_full_filter(zeep_client: zeep.Client) -> None:
    """Prove that FileTypes, FileFormats, FileName, dates and ClientAppGuid
    serialize against the local WSDL without ValidationError.
    """
    filt = DownloadFilter(
        file_types=[DownloadFileType.VYPIS, DownloadFileType.AVIZO],
        file_formats=[DownloadFileFormat.PDF, DownloadFileFormat.XML],
        filename="statement_2025.pdf",
        created_after=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        created_before=datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC),
        client_app_guid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    )
    request: dict[str, object] = {
        "ContractNumber": 123456,
        "PrevQueryTimestamp": datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC).isoformat(),
        "Filter": {
            "FileTypes": {"FileType": [ft.value for ft in filt.file_types]},
            "FileFormats": {"FileFormat": [ff.value for ff in filt.file_formats]},
            "FileName": filt.filename,
            "CreatedAfter": filt.created_after.isoformat(),
            "CreatedBefore": filt.created_before.isoformat(),
            "ClientAppGuid": filt.client_app_guid,
        },
    }

    # create_message validates the payload against the WSDL types
    msg = zeep_client.create_message(  # type: ignore[no-untyped-call]
        zeep_client.service, "GetDownloadFileList_v4", **request
    )
    assert msg is not None
    from lxml import etree

    xml_bytes = etree.tostring(msg)
    assert b"FileFormat" in xml_bytes
    assert b"PDF" in xml_bytes
    assert b"XML" in xml_bytes


def test_get_download_file_list_v4_serializes_minimal_filter(zeep_client: zeep.Client) -> None:
    """Only ContractNumber is truly required."""
    msg = zeep_client.create_message(  # type: ignore[no-untyped-call]
        zeep_client.service, "GetDownloadFileList_v4", ContractNumber=123456
    )
    assert msg is not None


def test_get_download_file_list_v4_serializes_file_formats_only(zeep_client: zeep.Client) -> None:
    """Regression guard: FileFormats must be accepted even when FileTypes is absent."""
    request: dict[str, object] = {
        "ContractNumber": 123456,
        "Filter": {
            "FileFormats": {"FileFormat": ["PDF", "TXT"]},
        },
    }
    msg = zeep_client.create_message(  # type: ignore[no-untyped-call]
        zeep_client.service, "GetDownloadFileList_v4", **request
    )
    assert msg is not None
