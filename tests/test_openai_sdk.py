"""Prove the official OpenAI Python SDK works unmodified against the gateway."""
import httpx
import pytest

from tests.conftest import make_app

openai = pytest.importorskip("openai")


async def test_openai_sdk_chat_and_models():
    app = make_app()
    async with app.router.lifespan_context(app):
        http_client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                        base_url="http://test/v1")
        oai = openai.AsyncOpenAI(api_key="test-key", base_url="http://test/v1",
                                 http_client=http_client)

        models = await oai.models.list()
        ids = [m.id for m in models.data]
        assert "agent_default" in ids

        resp = await oai.chat.completions.create(
            model="agent_default",
            messages=[{"role": "user", "content": "Hello via SDK"}],
        )
        assert resp.choices[0].message.content
        assert "Hello via SDK" in resp.choices[0].message.content

        await http_client.aclose()


async def test_openai_sdk_streaming():
    app = make_app()
    async with app.router.lifespan_context(app):
        http_client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                        base_url="http://test/v1")
        oai = openai.AsyncOpenAI(api_key="k", base_url="http://test/v1", http_client=http_client)
        stream = await oai.chat.completions.create(
            model="agent_default",
            messages=[{"role": "user", "content": "stream via SDK"}],
            stream=True,
        )
        pieces = []
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                pieces.append(chunk.choices[0].delta.content)
        assert "".join(pieces)
        await http_client.aclose()
