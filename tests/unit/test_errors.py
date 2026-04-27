from csob_ceb_bc.errors import (
    CsobBCDuplicateUploadError,
    CsobBCError,
    CsobBCPermanentError,
    CsobBCRateLimitError,
    CsobBCRetryableError,
    CsobBCSoapError,
    CsobBCSoapFault,
)


def test_base_error_attributes():
    err = CsobBCError(
        "safe msg",
        operation="op",
        contract_number_redacted="123***",
        ticket_id="T-123",
        retryable=False,
        permanent=True,
        cause=None,
        safe_message="safe msg",
    )
    assert err.operation == "op"
    assert err.ticket_id == "T-123"
    assert err.retryable is False
    assert err.permanent is True
    assert err.safe_message == "safe msg"
    assert str(err) == "safe msg"


def test_soap_fault_maps_fault_code():
    err = CsobBCSoapFault(
        "SOAP fault",
        fault_code="1101",
        fault_string="Rate limit",
        ticket_id="T-456",
        retryable=True,
        permanent=False,
        safe_message="SOAP fault",
    )
    assert err.fault_code == "1101"
    assert err.fault_string == "Rate limit"
    assert issubclass(CsobBCSoapFault, CsobBCSoapError)


def test_rate_limit_is_retryable():
    err = CsobBCRateLimitError("rate limited")
    assert err.retryable is True
    assert issubclass(CsobBCRateLimitError, CsobBCRetryableError)


def test_duplicate_upload_is_permanent():
    err = CsobBCDuplicateUploadError("duplicate")
    assert err.permanent is True
    assert issubclass(CsobBCDuplicateUploadError, CsobBCPermanentError)
