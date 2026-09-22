"""
Rate Limiting Tests (PRD Section 11.3)
=======================================
Tests for the in-memory sliding-window rate limiter middleware.
"""

import time
import pytest
from httpx import AsyncClient

from app.core.rate_limit import _SlidingWindowCounter


# ---------------------------------------------------------------------------
# Unit tests for _SlidingWindowCounter
# ---------------------------------------------------------------------------

class TestSlidingWindowCounter:
    def test_allows_requests_within_limit(self):
        counter = _SlidingWindowCounter(window_seconds=60, max_requests=5)
        for _ in range(5):
            allowed, remaining = counter.is_allowed("user1")
            assert allowed is True
        assert remaining == 0

    def test_rejects_when_limit_exceeded(self):
        counter = _SlidingWindowCounter(window_seconds=60, max_requests=3)
        for _ in range(3):
            counter.is_allowed("user1")
        allowed, remaining = counter.is_allowed("user1")
        assert allowed is False
        assert remaining == 0

    def test_different_keys_independent(self):
        counter = _SlidingWindowCounter(window_seconds=60, max_requests=2)
        counter.is_allowed("user1")
        counter.is_allowed("user1")
        # user1 is now at limit
        allowed1, _ = counter.is_allowed("user1")
        assert allowed1 is False

        # user2 should still be allowed
        allowed2, remaining2 = counter.is_allowed("user2")
        assert allowed2 is True
        assert remaining2 == 1

    def test_window_expiry_allows_new_requests(self):
        counter = _SlidingWindowCounter(window_seconds=1, max_requests=2)
        counter.is_allowed("user1")
        counter.is_allowed("user1")
        # At limit
        assert counter.is_allowed("user1")[0] is False

        # Wait for window to expire
        time.sleep(1.1)

        allowed, remaining = counter.is_allowed("user1")
        assert allowed is True
        assert remaining == 1

    def test_empty_key_is_allowed(self):
        counter = _SlidingWindowCounter(window_seconds=60, max_requests=5)
        allowed, remaining = counter.is_allowed("")
        assert allowed is True
        assert remaining == 4

    def test_remaining_count_accurate(self):
        counter = _SlidingWindowCounter(window_seconds=60, max_requests=10)
        for i in range(7):
            allowed, remaining = counter.is_allowed("k")
            assert remaining == 9 - i


# ---------------------------------------------------------------------------
# Integration tests — rate limiter middleware behavior
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestRateLimitMiddleware:
    async def test_non_rate_limited_endpoint_unaffected(self, client: AsyncClient):
        """Endpoints not covered by rate limiting should be unaffected."""
        res = await client.get("/api/health")
        assert res.status_code == 200
