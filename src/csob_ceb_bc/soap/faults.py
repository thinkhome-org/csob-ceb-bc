from __future__ import annotations

from csob_ceb_bc.errors import (
    CsobBCError,
    CsobBCPermanentError,
    CsobBCRateLimitError,
    CsobBCRetryableError,
    CsobBCSoapFault,
)

_FAULT_MAP: dict[str, type[CsobBCError]] = {
    "1000": CsobBCRetryableError,
    "1002": CsobBCPermanentError,
    "1011": CsobBCPermanentError,
    "1012": CsobBCPermanentError,
    "1101": CsobBCRateLimitError,
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
