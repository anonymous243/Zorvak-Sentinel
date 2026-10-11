import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from sentinel_core.rate_limiter import DistributedRateLimitMiddleware

@pytest.mark.asyncio
async def test_rate_limiting_enforcement_and_headers():
    app = FastAPI()
    app.add_middleware(DistributedRateLimitMiddleware)

    @app.get("/auth/signup")
    async def signup():
        return {"status": "ok"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check is not throttled
        for _ in range(10):
            res = await client.get("/health")
            assert res.status_code == 200

        # 2. /auth/signup limit is 5 requests per minute
        for i in range(5):
            res = await client.get("/auth/signup", headers={"x-tenant-id": "t1"})
            assert res.status_code == 200
            assert res.headers["X-RateLimit-Limit"] == "5"

        # 6th request triggers HTTP 429
        res_blocked = await client.get("/auth/signup", headers={"x-tenant-id": "t1"})
        assert res_blocked.status_code == 429
        assert res_blocked.headers["Retry-After"] == "60"
        assert res_blocked.headers["X-RateLimit-Limit"] == "5"
        assert "Rate limit exceeded" in res_blocked.json()["detail"]
