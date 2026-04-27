from csob_ceb_bc.errors import (
    CsobBCPermanentError,
    CsobBCRateLimitError,
    CsobBCRetryableError,
    CsobBCSoapFault,
)
from csob_ceb_bc.soap.faults import map_soap_fault


def test_map_1000_retryable():
    exc = map_soap_fault(fault_code="1000", fault_string="Internal", ticket_id="T1")
    assert isinstance(exc, CsobBCRetryableError)
    assert exc.ticket_id == "T1"


def test_map_1002_permanent():
    exc = map_soap_fault(fault_code="1002", fault_string="No BC", ticket_id="T2")
    assert isinstance(exc, CsobBCPermanentError)


def test_map_1011_permanent():
    exc = map_soap_fault(fault_code="1011", fault_string="Not registered", ticket_id="T3")
    assert isinstance(exc, CsobBCPermanentError)


def test_map_1012_permanent():
    exc = map_soap_fault(fault_code="1012", fault_string="Blocked", ticket_id="T4")
    assert isinstance(exc, CsobBCPermanentError)


def test_map_1101_rate_limit():
    exc = map_soap_fault(fault_code="1101", fault_string="Too many calls", ticket_id="T5")
    assert isinstance(exc, CsobBCRateLimitError)


def test_map_unknown_default_retryable():
    exc = map_soap_fault(fault_code="9999", fault_string="Unknown", ticket_id="T6")
    assert isinstance(exc, CsobBCSoapFault)
    assert exc.retryable is True
