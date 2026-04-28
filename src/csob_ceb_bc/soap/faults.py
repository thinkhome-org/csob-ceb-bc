from __future__ import annotations

from enum import StrEnum

from csob_ceb_bc.errors import (
    CsobBCBlockedError,
    CsobBCContractDisabledError,
    CsobBCError,
    CsobBCNotRegisteredError,
    CsobBCRateLimitError,
    CsobBCServerError,
    CsobBCSoapFault,
)


class SoapFaultCode(StrEnum):
    """Known ČSOB BC SOAP fault codes."""

    SERVER_ERROR = "1000"
    CONTRACT_DISABLED = "1002"
    NOT_REGISTERED = "1011"
    BLOCKED = "1012"
    RATE_LIMIT = "1101"


_FAULT_MAP: dict[str, type[CsobBCError]] = {
    SoapFaultCode.SERVER_ERROR: CsobBCServerError,
    SoapFaultCode.CONTRACT_DISABLED: CsobBCContractDisabledError,
    SoapFaultCode.NOT_REGISTERED: CsobBCNotRegisteredError,
    SoapFaultCode.BLOCKED: CsobBCBlockedError,
    SoapFaultCode.RATE_LIMIT: CsobBCRateLimitError,
}


def map_soap_fault(
    *,
    fault_code: str | None,
    fault_string: str | None,
    ticket_id: str | None,
) -> CsobBCError:
    code = fault_code or "UNKNOWN"
    msg = fault_string or f"SOAP Fault {code}"
    exc_cls = _FAULT_MAP.get(code, CsobBCSoapFault)

    if exc_cls is CsobBCSoapFault:
        return CsobBCSoapFault(
            msg,
            fault_code=code,
            fault_string=fault_string,
            ticket_id=ticket_id,
            retryable=True,
            permanent=False,
            safe_message=msg,
        )

    return exc_cls(
        msg,
        operation="soap",
        ticket_id=ticket_id,
        safe_message=msg,
    )
