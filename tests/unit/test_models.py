from datetime import UTC, datetime

import pytest

from csob_ceb_bc.models import (
    DownloadBatchResult,
    DownloadFile,
    DownloadFileStatus,
    DownloadFileType,
    DownloadFilter,
    SoapFaultInfo,
    UploadFile,
    UploadFinishStatus,
    UploadMode,
    UploadStartStatus,
)


def test_download_file_type_enum():
    assert DownloadFileType.VYPIS == "VYPIS"
    assert DownloadFileType.AVIZO == "AVIZO"
    assert DownloadFileType.KURZY == "KURZY"
    assert DownloadFileType.IMPPROT == "IMPPROT"


def test_download_file_format_enum():
    from csob_ceb_bc.models import DownloadFileFormat

    assert DownloadFileFormat.PDF == "PDF"
    assert DownloadFileFormat.TXT == "TXT"
    assert DownloadFileFormat.XML == "XML"
    assert DownloadFileFormat.BBGPC == "BBGPC"
    assert DownloadFileFormat.BBMT940 == "BBMT940"
    assert DownloadFileFormat.BBTXT == "BBTXT"
    assert DownloadFileFormat.BBBBF == "BBBBF"
    assert DownloadFileFormat.SEPAXML == "SEPAXML"
    assert DownloadFileFormat.MT942 == "MT942"
    assert DownloadFileFormat.BBF == "BBF"
    assert DownloadFileFormat.CAMT052 == "CAMT052"


def test_download_file_status_enum():
    assert DownloadFileStatus.R == "R"
    assert DownloadFileStatus.D == "D"
    assert DownloadFileStatus.F == "F"


def test_upload_mode_enum():
    assert UploadMode.IncludeIncorrect == "IncludeIncorrect"
    assert UploadMode.OnlyCorrect == "OnlyCorrect"
    assert UploadMode.AllOrNothing == "AllOrNothing"
    assert UploadMode.SignedAllOrNothing == "SignedAllOrNothing"


def test_upload_start_status_enum():
    assert UploadStartStatus.R == "R"
    assert UploadStartStatus.U == "U"


def test_upload_finish_status_enum():
    assert UploadFinishStatus.R == "R"
    assert UploadFinishStatus.I == "I"


def test_download_filter_defaults():
    f = DownloadFilter()
    assert f.file_types is None


def test_download_filter_with_types():
    f = DownloadFilter(file_types=[DownloadFileType.VYPIS, DownloadFileType.AVIZO])
    assert f.file_types == [DownloadFileType.VYPIS, DownloadFileType.AVIZO]


def test_download_filter_with_formats():
    from csob_ceb_bc.models import DownloadFileFormat

    f = DownloadFilter(file_formats=[DownloadFileFormat.PDF, DownloadFileFormat.XML])
    assert f.file_formats == [DownloadFileFormat.PDF, DownloadFileFormat.XML]


def test_download_filter_rejects_invalid_format():
    with pytest.raises(ValueError):
        DownloadFilter(file_formats=["CSV"])  # type: ignore[list-item]


def test_download_filter_rejects_naive_datetime():
    naive = datetime(2025, 1, 1, 0, 0, 0)
    with pytest.raises(ValueError):
        DownloadFilter(created_after=naive)
    with pytest.raises(ValueError):
        DownloadFilter(created_before=naive)


def test_download_filter_accepts_aware_datetime():
    aware = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    f = DownloadFilter(created_after=aware, created_before=aware)
    assert f.created_after == aware
    assert f.created_before == aware


def test_upload_file_validates_filename_max_length():
    with pytest.raises(ValueError):
        UploadFile(filename="x" * 51, format="XML SEPA", mode=UploadMode.AllOrNothing)
    # Direct call for coverage (pydantic-core may skip Python line tracing)
    with pytest.raises(ValueError):
        UploadFile._filename_max_length("x" * 51)


def test_upload_file_separator_validation():
    UploadFile(filename="test.xml", format="XML SEPA", mode=UploadMode.AllOrNothing, separator="|")
    UploadFile(filename="test.xml", format="XML SEPA", mode=UploadMode.AllOrNothing, separator=";;")
    with pytest.raises(ValueError):
        UploadFile(
            filename="test.xml",
            format="XML SEPA",
            mode=UploadMode.AllOrNothing,
            separator=",",
        )


def test_upload_file_signed_mode_no_skip_duplicates_promise():
    """SignedAllOrNothing must not allow skip_check_duplicates=True because bank ignores it."""
    with pytest.raises(ValueError):
        UploadFile(
            filename="test.xml",
            format="XML SEPA",
            mode=UploadMode.SignedAllOrNothing,
            skip_check_duplicates=True,
        )


def test_upload_file_hash_must_be_sha256():
    with pytest.raises(ValueError):
        UploadFile(filename="test.xml", format="XML SEPA", mode=UploadMode.AllOrNothing, hash="bad")
    with pytest.raises(ValueError):
        UploadFile(
            filename="test.xml",
            format="XML SEPA",
            mode=UploadMode.AllOrNothing,
            hash="a" * 32,
        )
    valid_sha = UploadFile(
        filename="test.xml",
        format="XML SEPA",
        mode=UploadMode.AllOrNothing,
        hash="a" * 64,
    )
    assert valid_sha.hash == "a" * 64
    # Direct calls for coverage
    assert UploadFile._hash_must_be_sha256(None) is None
    with pytest.raises(ValueError):
        UploadFile._hash_must_be_sha256("gg")
    with pytest.raises(ValueError):
        UploadFile._hash_must_be_sha256("g" * 64)


def test_download_file_model():
    f = DownloadFile(
        filename="stmt.pdf",
        type=DownloadFileType.VYPIS,
        format="PDF",
        creation_date_time=datetime.now(UTC),
        size=1024,
        status=DownloadFileStatus.D,
        url="https://example.com/file",
        upload_file_hash=None,
    )
    assert f.size == 1024
    assert f.url is not None
    assert f.format == "PDF"


def test_download_file_format_coercion():
    from csob_ceb_bc.models import DownloadFileFormat

    f = DownloadFile(
        filename="stmt.pdf",
        type=DownloadFileType.VYPIS,
        format="PDF",  # string coerced to enum
        creation_date_time=datetime.now(UTC),
        status=DownloadFileStatus.D,
    )
    assert f.format == DownloadFileFormat.PDF


def test_soap_fault_info_model():
    info = SoapFaultInfo(
        fault_code="1000",
        fault_string="Internal error",
        ticket_id="T-789",
    )
    assert info.fault_code == "1000"


def test_download_filter_guid_validation():
    valid_guid = "12345678-1234-1234-1234-123456789abc"
    f = DownloadFilter(client_app_guid=valid_guid)
    assert f.client_app_guid == valid_guid

    with pytest.raises(ValueError):
        DownloadFilter(client_app_guid="not-a-uuid")

    with pytest.raises(ValueError):
        DownloadFilter(client_app_guid="{12345678-1234-1234-1234-123456789abc}")


def test_download_batch_result():
    from datetime import UTC, datetime

    f = DownloadFile(
        filename="stmt.pdf",
        type=DownloadFileType.VYPIS,
        format="PDF",
        creation_date_time=datetime.now(UTC),
        size=1024,
        status=DownloadFileStatus.D,
        url="https://example.com/file",
        upload_file_hash=None,
    )
    result = DownloadBatchResult(
        downloaded=[f],
        pending=[],
        failed=[],
        cursor_advanced=True,
        query_timestamp=datetime.now(UTC),
    )
    assert result.has_pending_files is False
    assert len(result.downloaded) == 1

    pending_result = DownloadBatchResult(
        downloaded=[],
        pending=[f],
        failed=[],
        cursor_advanced=False,
    )
    assert pending_result.has_pending_files is True
