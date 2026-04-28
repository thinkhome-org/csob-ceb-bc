from csob_ceb_bc.errors import (
    CsobBCBlockedError,
    CsobBCContractDisabledError,
    CsobBCNotRegisteredError,
    CsobBCRateLimitError,
    CsobBCServerError,
    CsobBCSoapFault,
)
from csob_ceb_bc.soap.faults import SoapFaultCode, map_soap_fault


def test_map_1000_server_error():
    exc = map_soap_fault(fault_code="1000", fault_string="Internal", ticket_id="T1")
    assert isinstance(exc, CsobBCServerError)
    assert exc.ticket_id == "T1"
    assert exc.retryable is True


def test_map_1002_contract_disabled():
    exc = map_soap_fault(fault_code="1002", fault_string="No BC", ticket_id="T2")
    assert isinstance(exc, CsobBCContractDisabledError)
    assert exc.permanent is True


def test_map_1011_not_registered():
    exc = map_soap_fault(fault_code="1011", fault_string="Not registered", ticket_id="T3")
    assert isinstance(exc, CsobBCNotRegisteredError)
    assert exc.permanent is True


def test_map_1012_blocked():
    exc = map_soap_fault(fault_code="1012", fault_string="Blocked", ticket_id="T4")
    assert isinstance(exc, CsobBCBlockedError)
    assert exc.permanent is True


def test_map_1101_rate_limit():
    exc = map_soap_fault(fault_code="1101", fault_string="Too many calls", ticket_id="T5")
    assert isinstance(exc, CsobBCRateLimitError)
    assert exc.retryable is True


def test_map_unknown_default_retryable():
    exc = map_soap_fault(fault_code="9999", fault_string="Unknown", ticket_id="T6")
    assert isinstance(exc, CsobBCSoapFault)
    assert exc.retryable is True


def test_fault_code_enum_values():
    assert SoapFaultCode.SERVER_ERROR == "1000"
    assert SoapFaultCode.CONTRACT_DISABLED == "1002"
    assert SoapFaultCode.NOT_REGISTERED == "1011"
    assert SoapFaultCode.BLOCKED == "1012"
    assert SoapFaultCode.RATE_LIMIT == "1101"
