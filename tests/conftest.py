import httpx
import pytest_asyncio

from gateway.app import create_app
from gateway.config import Settings
from gateway.upstream.mock import MockAdapter


def make_app(**overrides):
    base = dict(upstream="mock", api_keys="", poll_interval=0.01, run_timeout=5.0)
    base.update(overrides)
    settings = Settings(**base)
    adapter = MockAdapter()
    return create_app(settings=settings, adapter=adapter)


@pytest_asyncio.fixture
async def client():
    app = make_app()
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
