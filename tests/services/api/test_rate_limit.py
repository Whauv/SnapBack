"""Tests for the in-memory rate limiter."""

from __future__ import annotations

import unittest
from unittest import mock

from fastapi import HTTPException

from services.api import rate_limit
from services.api.rate_limit import InMemoryRateLimiter


class RateLimiterTests(unittest.TestCase):
    def test_blocks_after_limit(self):
        limiter = InMemoryRateLimiter(limit=2, window_seconds=60)
        limiter.enforce("k")
        limiter.enforce("k")
        with self.assertRaises(HTTPException) as ctx:
            limiter.enforce("k")
        self.assertEqual(ctx.exception.status_code, 429)

    def test_separate_keys_are_independent(self):
        limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
        limiter.enforce("a")
        limiter.enforce("b")  # different key, should not raise

    def test_idle_buckets_are_evicted(self):
        limiter = InMemoryRateLimiter(limit=5, window_seconds=10)
        with mock.patch.object(rate_limit, "monotonic", return_value=100.0):
            limiter.enforce("old")
        self.assertIn("old", limiter._buckets)
        # Much later, a request on a different key evicts the elapsed bucket.
        with mock.patch.object(rate_limit, "monotonic", return_value=1000.0):
            limiter.enforce("new")
        self.assertNotIn("old", limiter._buckets)
        self.assertIn("new", limiter._buckets)


if __name__ == "__main__":
    unittest.main()
