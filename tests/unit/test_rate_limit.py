import time

from csob_ceb_bc.rate_limit import TokenBucketRateLimiter


def test_token_bucket_allows_within_limit():
    limiter = TokenBucketRateLimiter(capacity=3, refill_per_second=1.0)
    assert limiter.acquire() is True
    assert limiter.acquire() is True
    assert limiter.acquire() is True


def test_token_bucket_blocks_when_empty():
    limiter = TokenBucketRateLimiter(capacity=1, refill_per_second=0.1)
    assert limiter.acquire() is True
    assert limiter.acquire() is False
    time.sleep(11)
    assert limiter.acquire() is True


def test_token_bucket_tracks_consumed():
    limiter = TokenBucketRateLimiter(capacity=5, refill_per_second=1.0)
    limiter.acquire()
    limiter.acquire()
    assert limiter.consumed() == 2
