"""In-memory API rate limiting."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic

from fastapi import HTTPException


@dataclass
class WindowBucket:
    timestamps: deque[float] = field(default_factory=deque)


class InMemoryRateLimiter:
    def __init__(self, *, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._buckets: dict[str, WindowBucket] = {}
        self._lock = Lock()

    def _prune(self, bucket: WindowBucket, now: float) -> None:
        threshold = now - self.window_seconds
        while bucket.timestamps and bucket.timestamps[0] <= threshold:
            bucket.timestamps.popleft()

    def enforce(self, key: str) -> None:
        now = monotonic()
        with self._lock:
            bucket = self._buckets.setdefault(key, WindowBucket())
            self._prune(bucket, now)
            if len(bucket.timestamps) >= self.limit:
                raise HTTPException(status_code=429, detail="Rate limit exceeded. Please retry shortly.")
            bucket.timestamps.append(now)
