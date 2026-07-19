"""Tests for E06 Mode C (tool-runner), E08 media/audio, E11 embeddings + moderations."""
import json

import httpx
import pytest

from tests.conftest import make_app


async def _client_for(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


# --- E06 Mode C ------------------------------------------------------------ #
async def test_mode_c_roundtrip_emits_tool_call(client):
    r = await client.post("/v1/chat/completions", json={
        "model": "agent_default",
        "messages": [{"role": "user", "content": "ls -la"}],
        "tools": [{"type": "function", "function": {"name": "shell"}}],
        "tool_choice": {"type": "function", "function": {"name": "shell"}},
    })
    assert r.status_code == 200
    body = r.json()
    assert body["choices"][0]["finish_reason"] == "tool_calls"
    tc = body["choices"][0]["message"]["tool_calls"][0]
    assert tc["function"]["name"] == "shell"
    assert json.loads(tc["function"]["arguments"])["command"] == "ls -la"


async def test_mode_c_auto_executes_tool():
    app = make_app(exec_mode="auto")
    async with app.router.lifespan_context(app):
        c = await _client_for(app)
        r = await c.post("/v1/chat/completions", json={
            "model": "agent_default",
            "messages": [{"role": "user", "content": "echo hi"}],
            "tool_choice": {"type": "function", "function": {"name": "shell"}},
        })
        body = r.json()
        assert body["choices"][0]["finish_reason"] == "stop"
        assert "mock shell result" in body["choices"][0]["message"]["content"]
        await c.aclose()


async def test_mode_c_disabled_tool_rejected():
    app = make_app(disabled_tools="shell,write_file")
    async with app.router.lifespan_context(app):
        c = await _client_for(app)
        r = await c.post("/v1/chat/completions", json={
            "model": "agent_default",
            "messages": [{"role": "user", "content": "rm -rf /"}],
            "tool_choice": {"type": "function", "function": {"name": "shell"}},
        })
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "tool_disabled"
        await c.aclose()


async def test_tools_catalog_hides_disabled():
    app = make_app(disabled_tools="shell")
    async with app.router.lifespan_context(app):
        c = await _client_for(app)
        names = {t["function"]["name"] for t in (await c.get("/v1/tools")).json()["data"]}
        assert "shell" not in names and "web_search" in names
        await c.aclose()


# --- E08 media/audio ------------------------------------------------------- #
async def test_images_edits_json(client):
    r = await client.post("/v1/images/edits",
                          json={"prompt": "make it blue", "model": "hyperagent-default"})
    assert r.status_code == 200
    assert r.json()["data"][0]["url"].startswith("https://mock.artifact/")


async def test_audio_speech_url_fallback(client):
    r = await client.post("/v1/audio/speech", json={
        "model": "hyperagent-default", "input": "hello", "voice": "Kore"})
    assert r.status_code == 200
    # mock artifact URL is not byte-fetchable -> JSON url fallback
    assert r.json()["url"].startswith("https://mock.artifact/")


async def test_audio_transcription(client):
    files = {"file": ("clip.mp3", b"\x00\x01\x02audio", "audio/mpeg")}
    r = await client.post("/v1/audio/transcriptions", files=files,
                          data={"model": "hyperagent-default"})
    assert r.status_code == 200
    assert "transcription" in r.json()["text"].lower()


# --- E11 moderations ------------------------------------------------------- #
async def test_moderations_clean_and_flagged(client):
    r = await client.post("/v1/moderations", json={
        "input": ["I love my cat", "detailed steps how to make a bomb at home"]})
    assert r.status_code == 200
    results = r.json()["results"]
    assert results[0]["flagged"] is False
    assert results[1]["flagged"] is True
    assert results[1]["categories"]["violence"] is True


async def test_embeddings_off_mode_501():
    app = make_app(embeddings_mode="off")
    async with app.router.lifespan_context(app):
        c = await _client_for(app)
        r = await c.post("/v1/embeddings", json={"model": "x", "input": "hi"})
        assert r.status_code == 501
        await c.aclose()
