from __future__ import annotations


class CsobBCError(Exception):
    """Base exception for all SDK errors."""

    def __init__(
        self,
        message: str,
        *,
        operation: str | None = None,
        contract_number_redacted: str | None = None,
        ticket_id: str | None = None,
        retryable: bool = False,
        permanent: bool = False,
        cause: Exception | None = None,
        safe_message: str = "",
    ) -> None:
        super().__init__(message)
        self.operation = operation
        self.contract_number_redacted = contract_number_redacted
        self.ticket_id = ticket_id
        self.retryable = retryable
        self.permanent = permanent
        self.cause = cause
        self.safe_message = safe_message or message


class CsobBCConfigError(CsobBCError):
    """Invalid configuration."""


class CsobBCCertificateError(CsobBCError):
    """Certificate loading or validation error."""


class CsobBCSoapError(CsobBCError):
    """SOAP communication error."""


class CsobBCSoapFault(CsobBCSoapError):
    """Mapped SOAP Fault response."""

    def __init__(
        self,
        message: str,
        *,
        fault_code: str | None = None,
        fault_string: str | None = None,
        ticket_id: str | None = None,
        retryable: bool = False,
        permanent: bool = False,
        safe_message: str = "",
    ) -> None:
        super().__init__(
            message,
            operation="soap",
            ticket_id=ticket_id,
            retryable=retryable,
            permanent=permanent,
            safe_message=safe_message,
        )
        self.fault_code = fault_code
        self.fault_string = fault_string


class CsobBCHttpError(CsobBCError):
    """HTTP transfer error."""


class CsobBCRetryableError(CsobBCError):
    """Base for errors that may be retried."""

    def __init__(self, message: str, **kwargs: object) -> None:
        kwargs.setdefault("retryable", True)
        kwargs.setdefault("permanent", False)
        super().__init__(message, **kwargs)


class CsobBCPermanentError(CsobBCError):
    """Base for errors that must not be retried automatically."""

    def __init__(self, message: str, **kwargs: object) -> None:
        kwargs.setdefault("retryable", False)
        kwargs.setdefault("permanent", True)
        super().__init__(message, **kwargs)


class CsobBCRateLimitError(CsobBCRetryableError):
    """SOAP 1101 or HTTP 429 rate limit."""


class CsobBCDownloadError(CsobBCError):
    """Download workflow error."""


class CsobBCUploadError(CsobBCError):
    """Upload workflow error."""


class CsobBCDuplicateUploadError(CsobBCPermanentError):
    """Upload rejected as duplicate."""


class CsobBCStateError(CsobBCError):
    """State persistence error."""


class CsobBCProtocolError(CsobBCError):
    """Unexpected protocol / malformed response."""
