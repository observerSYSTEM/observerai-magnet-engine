from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, *, key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
        now = time.monotonic()
        window_start = now - window_seconds

        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] <= window_start:
                bucket.popleft()

            if len(bucket) >= limit:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                return False, retry_after, len(bucket)

            bucket.append(now)
            return True, 0, len(bucket)

    def clear(self) -> None:
        with self._lock:
            self._buckets.clear()


rate_limiter = InMemoryRateLimiter()


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"


def clear_rate_limit_state() -> None:
    rate_limiter.clear()


def rate_limit(name: str, *, limit: int, window_seconds: int):
    async def dependency(request: Request) -> None:
        ip_address = _client_ip(request)
        key = f"{name}:{ip_address}"
        allowed, retry_after, request_count = rate_limiter.hit(
            key=key,
            limit=limit,
            window_seconds=window_seconds,
        )

        if not allowed:
            logger.warning(
                "Rate limit exceeded | route=%s method=%s ip=%s window=%ss limit=%s",
                name,
                request.method,
                ip_address,
                window_seconds,
                limit,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down and try again shortly.",
                headers={"Retry-After": str(retry_after)},
            )

        warning_threshold = max(1, int(limit * 0.8))
        if request_count >= warning_threshold:
            logger.warning(
                "Suspicious repeated access detected | route=%s method=%s ip=%s count=%s window=%ss",
                name,
                request.method,
                ip_address,
                request_count,
                window_seconds,
            )

    return dependency
