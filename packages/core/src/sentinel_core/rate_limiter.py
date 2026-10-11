"""
Distributed rate limiter for ZORVAK SENTINEL API.
Supports Redis-backed sliding window / token bucket in production,
with in-memory sliding window fallback for local development/testing.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Default tier limits (requests per minute)
DEFAULT_LIMITS: dict[str, int] = {
    "/auth/login": 10,
    "/auth/signup": 5,
    "/agents": 60,
    "/policies": 120,
    "default": 300,
}

class SlidingWindowMemoryLimiter:
    def __init__(self):
        # key -> list of timestamps (float)
        self._history: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, limit: int, window_seconds: float = 60.0) -> bool:
        now = time.time()
        cutoff = now - window_seconds
        timestamps = [ts for ts in self._history[key] if ts > cutoff]
        if len(timestamps) >= limit:
            self._history[key] = timestamps
            return False
        timestamps.append(now)
        self._history[key] = timestamps
        return True


class DistributedRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_url: Optional[str] = None):
        super().__init__(app)
        self.app_env = os.getenv("APP_ENV", "development")
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.redis_client = None

        if self.app_env in ("production", "staging"):
            if not self.redis_url:
                raise RuntimeError(
                    "FATAL SECURITY MISCONFIGURATION: REDIS_URL must be configured in production/staging. "
                    "Silent fallback to in-memory rate limiting is forbidden across distributed instances."
                )
        
        if self.redis_url:
            try:
                import redis.asyncio as redis
                self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            except ImportError:
                if self.app_env in ("production", "staging"):
                    raise RuntimeError("redis package is required for production distributed rate limiting")
                self.redis_client = None

        self._memory_limiter = SlidingWindowMemoryLimiter()

    def _resolve_limit(self, path: str) -> int:
        for prefix, limit in DEFAULT_LIMITS.items():
            if prefix != "default" and path.startswith(prefix):
                return limit
        return DEFAULT_LIMITS["default"]

    async def dispatch(self, request: Request, call_next):
        # Health and readiness probes are never rate limited
        if request.url.path in ("/health", "/ready"):
            return await call_next(request)

        client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.client.host if request.client else "unknown"

        tenant_id = request.headers.get("x-tenant-id", "global")
        path = request.url.path
        limit = self._resolve_limit(path)
        rate_key = f"rate:{tenant_id}:{client_ip}:{path}"

        allowed = True
        if self.redis_client:
            try:
                now_ts = time.time()
                cutoff_ts = now_ts - 60.0
                pipe = self.redis_client.pipeline()
                pipe.zremrangebyscore(rate_key, 0, cutoff_ts)
                pipe.zcard(rate_key)
                pipe.zadd(rate_key, {str(now_ts): now_ts})
                pipe.expire(rate_key, 65)
                results = await pipe.execute()
                current_count = results[1]
                if current_count >= limit:
                    allowed = False
            except Exception:
                # Fail-closed for sensitive authentication and agent onboarding endpoints
                if path.startswith(("/auth", "/agents")):
                    return Response(
                        content='{"detail":"Rate limiter service unavailable. Access denied for security."}',
                        status_code=503,
                        media_type="application/json",
                    )
                # Fail-open for non-sensitive read/monitoring traffic
                allowed = True
        else:
            allowed = self._memory_limiter.is_allowed(rate_key, limit, window_seconds=60.0)

        if not allowed:
            return Response(
                content='{"detail":"Rate limit exceeded. Too many requests."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(limit),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        return response
