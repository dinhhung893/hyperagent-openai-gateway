"""API-level tests through ASGI with the mock upstream."""
import json

import httpx
import pytest

from tests.conftest import make_app


async def test_health(client):
    r = await client.get("/v1/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


async def test_models(client):
    r = await client.get("/v1/models", headers={"authorization": "Bearer x"})
    assert r.status_code == 200
    data = r.json()
    assert data["object"] == "list"
    ids = [m["id"] for m in data["data"]]
    assert "agent_default" in ids
    assert data["data"][0]["owned_by"] == "hyperagent"


async def test_chat_completion_non_stream(client):
    r = await client.post("/v1/chat/completions", json={
        "model": "agent_default",
        "messages": [{"role": "user", "content": "Hello there"}],
    })
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert "Hello there" in body["choices"][0]["message"]["content"]
    assert body["choices"][0]["finish_reason"] == "stop"
    assert body["usage"]["total_tokens"] >= 1


async def test_chat_completion_reserved_model_alias(client):
    r = await client.post("/v1/chat/completions", json={
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "map alias to default agent"}],
    })
    assert r.status_code == 200


async def test_chat_tool_bridge_observability(client):
    r = await client.post("/v1/chat/completions", json={
        "model": "agent_default",
        "messages": [{"role": "user", "content": "shell: ls -la"}],
    })
    body = r.json()
    tcs = body["choices"][0]["message"]["tool_calls"]
    assert tcs[0]["function"]["name"] == "shell"
    assert body["choices"][0]["finish_reason"] == "tool_calls"


async def test_chat_completion_stream(client):
    async with client.stream("POST", "/v1/chat/completions", json={
        "model": "agent_default",
        "messages": [{"role": "user", "content": "stream me"}],
        "stream": True,
        "stream_options": {"include_usage": True},
    }) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        chunks = [line async for line in resp.aiter_lines() if line.startswith("data:")]
    assert chunks[-1] == "data: [DONE]"
    # first real chunk carries the assistant role
    first = json.loads(chunks[0][len("data: "):])
    assert first["object"] == "chat.completion.chunk"
    assert first["choices"][0]["delta"].get("role") == "assistant"
    # a usage chunk appears before DONE
    usage_seen = any('"usage"' in c for c in chunks)
    assert usage_seen


async def test_tools_catalog(client):
    r = await client.get("/v1/tools", headers={"authorization": "Bearer x"})
    data = r.json()["data"]
    names = {t["function"]["name"] for t in data}
    assert {"shell", "write_file", "web_search", "generate_image"} <= names


async def test_legacy_completions(client):
    r = await client.post("/v1/completions", json={"model": "agent_default", "prompt": "hi"})
    assert r.status_code == 200
    assert r.json()["object"] == "text_completion"


async def test_responses_sync(client):
    r = await client.post("/v1/responses", json={
        "model": "agent_default", "input": "Summarize the plan"})
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "response" and body["status"] == "completed"
    assert "Summarize the plan" in body["output_text"]


async def test_responses_background_then_poll(client):
    r = await client.post("/v1/responses", json={
        "model": "agent_default", "input": "bg task", "background": True})
    rid = r.json()["id"]
    assert r.json()["status"] == "in_progress"
    r2 = await client.get(f"/v1/responses/{rid}")
    assert r2.status_code == 200
    assert r2.json()["status"] == "completed"


async def test_files_upload(client):
    files = {"file": ("note.txt", b"hello bytes", "text/plain")}
    r = await client.post("/v1/files", files=files, data={"purpose": "assistants"})
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "file" and body["bytes"] == 11
    fid = body["id"]
    r2 = await client.get(f"/v1/files/{fid}")
    assert r2.status_code == 200


async def test_embeddings_fallback(client):
    r = await client.post("/v1/embeddings", json={"model": "x", "input": "hello world"})
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "list"
    emb = body["data"][0]["embedding"]
    assert len(emb) == 1536
    # deterministic: same text -> same vector
    r2 = await client.post("/v1/embeddings", json={"model": "x", "input": "hello world"})
    assert r2.json()["data"][0]["embedding"][:8] == emb[:8]


async def test_images_generations(client):
    r = await client.post("/v1/images/generations",
                          json={"prompt": "a red cube", "model": "hyperagent-default"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data[0]["url"].startswith("https://mock.artifact/")


async def test_unknown_model_404(client):
    r = await client.post("/v1/chat/completions", json={
        "model": "no-such-agent", "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "model_not_found"


async def test_auth_enforced():
    app = make_app(api_keys="secret1,secret2")
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/v1/chat/completions", json={
                "model": "agent_default", "messages": [{"role": "user", "content": "hi"}]})
            assert r.status_code == 401
            r2 = await c.post("/v1/chat/completions",
                              headers={"authorization": "Bearer secret1"},
                              json={"model": "agent_default",
                                    "messages": [{"role": "user", "content": "hi"}]})
            assert r2.status_code == 200


async def test_latin1_body_is_tolerated(client):
    # PowerShell 5.1 sends non-ASCII bodies as Latin-1/CP1252; the gateway must
    # repair the encoding instead of failing to parse the JSON.
    body = '{"model":"agent_default","messages":[{"role":"user","content":"Xin chào"}]}'
    r = await client.post("/v1/chat/completions", content=body.encode("latin-1"),
                          headers={"content-type": "application/json"})
    assert r.status_code == 200
    assert "Xin ch" in r.json()["choices"][0]["message"]["content"]


async def test_chat_is_stateless(client):
    # Chat is stateless: each call is a fresh self-contained thread (clients
    # resend full history), so fingerprints (threadIds) differ.
    r1 = await client.post("/v1/chat/completions", json={
        "model": "agent_default", "messages": [{"role": "user", "content": "first"}]})
    r2 = await client.post("/v1/chat/completions", json={
        "model": "agent_default", "messages": [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "second"}]})
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["system_fingerprint"] != r2.json()["system_fingerprint"]
    # full history is carried into the flattened prompt
    assert "second" in r2.json()["choices"][0]["message"]["content"]
