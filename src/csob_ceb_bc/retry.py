from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from csob_ceb_bc.errors import (
    CsobBCError,
    CsobBCHttpError,
    CsobBCRateLimitError,
    CsobBCRetryableError,
    CsobBCSoapFault,
)

T = TypeVar("T")

logger = logging.getLogger("csob_ceb_bc.retry")


def _is_retryable(exc: BaseException) -> bool:
    """Return True if the exception should trigger a retry."""
    if isinstance(exc, CsobBCRateLimitError):
        return True
    if isinstance(exc, CsobBCRetryableError):
        return True
    if isinstance(exc, CsobBCSoapFault) and exc.retryable:
        return True
    if isinstance(exc, CsobBCHttpError) and exc.retryable:
        return True
    return isinstance(exc, CsobBCError) and exc.retryable


def retry_soap(
    max_attempts: int = 3,
    max_wait_seconds: float = 300.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Tenacity retry decorator for SOAP calls.

    Retries on retryable errors with exponential backoff + jitter.
    Rate-limit errors (1101) get a longer initial wait.
    """
    return retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=1, max=max_wait_seconds, jitter=2),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )


def retry_rest(
    max_attempts: int = 3,
    max_wait_seconds: float = 120.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Tenacity retry decorator for REST transfers.

    Retries on retryable HTTP errors and timeouts.
    """
    return retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=1, max=max_wait_seconds, jitter=2),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
