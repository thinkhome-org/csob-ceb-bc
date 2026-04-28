from datetime import UTC, datetime

import pytest

from csob_ceb_bc.models import (
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


def test_upload_file_hash_must_be_hex():
    with pytest.raises(ValueError):
        UploadFile(filename="test.xml", format="XML SEPA", mode=UploadMode.AllOrNothing, hash="bad")
    valid_sha = UploadFile(
        filename="test.xml",
        format="XML SEPA",
        mode=UploadMode.AllOrNothing,
        hash="a" * 64,
    )
    assert valid_sha.hash == "a" * 64
    valid_md5 = UploadFile(
        filename="test.xml",
        format="XML SEPA",
        mode=UploadMode.AllOrNothing,
        hash="a" * 32,
    )
    assert valid_md5.hash == "a" * 32
    # Direct calls for coverage
    assert UploadFile._hash_must_be_hex(None) is None
    with pytest.raises(ValueError):
        UploadFile._hash_must_be_hex("gg")
    with pytest.raises(ValueError):
        UploadFile._hash_must_be_hex("g" * 64)


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


def test_soap_fault_info_model():
    info = SoapFaultInfo(
        fault_code="1000",
        fault_string="Internal error",
        ticket_id="T-789",
    )
    assert info.fault_code == "1000"
