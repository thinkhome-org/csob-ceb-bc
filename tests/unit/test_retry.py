from unittest.mock import MagicMock

import pytest

from csob_ceb_bc.errors import (
    CsobBCHttpError,
    CsobBCRateLimitError,
    CsobBCRetryableError,
    CsobBCSoapFault,
)
from csob_ceb_bc.retry import retry_rest, retry_soap


def test_retry_soap_eventually_succeeds():
    mock = MagicMock(side_effect=[
        CsobBCRetryableError("temp fail"),
        CsobBCRetryableError("temp fail"),
        "success",
    ])

    @retry_soap(max_attempts=3)
    def call():
        result = mock()
        if isinstance(result, Exception):
            raise result
        return result

    assert call() == "success"
    assert mock.call_count == 3


def test_retry_soap_reraises_after_exhaustion():
    mock = MagicMock(side_effect=CsobBCRateLimitError("rate limited"))

    @retry_soap(max_attempts=2)
    def call():
        raise mock()

    with pytest.raises(CsobBCRateLimitError):
        call()
    assert mock.call_count == 2


def test_retry_rest_reraises_permanent():
    mock = MagicMock(side_effect=CsobBCHttpError("404", permanent=True, retryable=False))

    @retry_rest(max_attempts=2)
    def call():
        raise mock()

    with pytest.raises(CsobBCHttpError):
        call()
    assert mock.call_count == 1


def test_retry_soap_skips_permanent():
    mock = MagicMock(
        side_effect=CsobBCSoapFault(
            "blocked", fault_code="1012", permanent=True, retryable=False
        )
    )

    @retry_soap(max_attempts=3)
    def call():
        raise mock()

    with pytest.raises(CsobBCSoapFault):
        call()
    assert mock.call_count == 1
