"""Token bucket rate limiter for Readwise API."""

from __future__ import annotations

import asyncio
import time


class TokenBucketRateLimiter:
    """Token bucket rate limiter.

    Allows `rate` requests per `period` seconds, with burst capacity equal to `rate`.
    """

    def __init__(self, rate: int, period: float = 60.0) -> None:
        self.rate = rate
        self.period = period
        self.tokens = float(rate)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.rate, self.tokens + elapsed * (self.rate / self.period))
        self.last_refill = now

    async def acquire(self) -> None:
        """Wait until a token is available, then consume it."""
        async with self._lock:
            self._refill()
            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) * (self.period / self.rate)
                await asyncio.sleep(wait_time)
                self._refill()
            self.tokens -= 1.0
