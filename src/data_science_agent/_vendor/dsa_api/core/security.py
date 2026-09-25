"""API security primitives: response headers + IP rate limiting (zero new deps)."""

from __future__ import annotations

import asyncio
import hmac
import logging
import time
from collections import deque
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

log = logging.getLogger(__name__)

# Path rules: (prefix, method, requests per 60 s). Only expensive endpoints are
# limited; reads stay unlimited so dashboards/polling are unaffected.
_DEFAULT_RULES: tuple[tuple[str, str, int], ...] = (
    ("/api/v1/analysis", "POST", 60),
    ("/api/v1/datasets", "POST", 30),
    ("/api/v1/experiments", "POST", 60),
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Minimal hardening headers for a JSON API (no cookies, no credentials)."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response


class RateLimiter:
    """In-memory sliding-window limiter (single process; LB needs Redis)."""

    def __init__(self, max_requests: int, window_s: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        now = time.monotonic()
        async with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self.window_s:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(now)
            return True

    async def clear(self) -> None:
        async with self._lock:
            self._hits.clear()


# One limiter per rule index; shared across requests in this process.
_limiters: list[RateLimiter] = [RateLimiter(n) for _, _, n in _DEFAULT_RULES]


async def clear_rate_limit_state() -> None:
    for limiter in _limiters:
        await limiter.clear()


def _client_ip(request: Request) -> str:
    client = request.client
    if client is not None:
        return str(client.host)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """429s expensive endpoints per IP; disabled via DSA_RATE_LIMIT_ENABLED=false."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        from dsa_api.core.config import settings  # deferred: avoids import cycle

        if not settings.rate_limit_enabled:
            return await call_next(request)
        for i, (prefix, method, _) in enumerate(_DEFAULT_RULES):
            if request.method == method and request.url.path.startswith(prefix):
                # Per-test overrides of settings limits rebuild that rule's limiter.
                want = {
                    "/api/v1/analysis": settings.rate_limit_analysis_per_min,
                    "/api/v1/datasets": settings.rate_limit_upload_per_min,
                    "/api/v1/experiments": settings.rate_limit_analysis_per_min,
                }[prefix]
                if _limiters[i].max_requests != want:
                    _limiters[i] = RateLimiter(want)
                key = f"{_client_ip(request)}:{prefix}"
                if not await _limiters[i].allow(key):
                    log.warning("rate limit exceeded", extra={"ip": key, "path": prefix})
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded. Please retry shortly."},
                        headers={"Retry-After": "60"},
                    )
                break
        return await call_next(request)


# Probes and preflight never require auth (hosting health checks, browsers).
_AUTH_PUBLIC_PATHS = frozenset({"/health", "/ready", "/version"})


class AuthMiddleware(BaseHTTPMiddleware):
    """Opt-in bearer-token auth. No-op unless DSA_AUTH_TOKEN is set."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        from dsa_api.core.config import settings  # deferred: avoids import cycle

        token = settings.auth_token
        if (
            not token
            or request.url.path in _AUTH_PUBLIC_PATHS
            or request.method == "OPTIONS"
            or not request.url.path.startswith("/api/")
        ):
            return await call_next(request)
        presented = request.headers.get("authorization", "")
        expected = f"Bearer {token}"
        if not presented or not hmac.compare_digest(presented, expected):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        return await call_next(request)
