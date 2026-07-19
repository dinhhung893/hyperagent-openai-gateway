"""E07 Responses API (stream/cancel/input_items) and E09 file lifecycle."""
import httpx
import pytest

from tests.conftest import make_app


async def _client_for(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


# --- E07 ------------------------------------------------------------------- #
async def test_responses_stream(client):
    async with client.stream("POST", "/v1/responses", json={
        "model": "agent_default", "input": "stream this", "stream": True,
    }) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        lines = [l async for l in resp.aiter_lines()]
    joined = "\n".join(lines)
    assert "response.created" in joined
    assert "response.output_text.delta" in joined
    assert "response.completed" in joined
    assert any(l.strip() == "data: [DONE]" for l in lines)


async def test_responses_cancel(client):
    r = await client.post("/v1/responses", json={
        "model": "agent_default", "input": "bg", "background": True})
    rid = r.json()["id"]
    rc = await client.post(f"/v1/responses/{rid}/cancel")
    assert rc.status_code == 200 and rc.json()["status"] == "cancelled"
    rg = await client.get(f"/v1/responses/{rid}")
    assert rg.json()["status"] == "cancelled"


async def test_responses_chain_carries_prior_context(client):
    r1 = await client.post("/v1/responses", json={
        "model": "agent_default", "input": "Remember the code SPARROW-42."})
    rid = r1.json()["id"]
    r2 = await client.post("/v1/responses", json={
        "model": "agent_default", "input": "What is the code?",
        "previous_response_id": rid})
    # prior context is reconstructed into the new prompt (mock echoes it back)
    assert "SPARROW-42" in r2.json()["output_text"]


async def test_responses_input_items(client):
    r = await client.post("/v1/responses", json={"model": "agent_default", "input": "remember XYZ"})
    rid = r.json()["id"]
    ri = await client.get(f"/v1/responses/{rid}/input_items")
    data = ri.json()["data"]
    assert any("remember XYZ" in it["content"][0]["text"] for it in data)


# --- E09 ------------------------------------------------------------------- #
async def test_files_list_content_delete(client):
    up = await client.post("/v1/files", files={"file": ("n.txt", b"hello", "text/plain")},
                           data={"purpose": "assistants"})
    fid = up.json()["id"]
    lst = await client.get("/v1/files")
    assert any(f["id"] == fid for f in lst.json()["data"])
    cont = await client.get(f"/v1/files/{fid}/content")
    assert cont.status_code == 200 and cont.content == b"hello"
    d = await client.delete(f"/v1/files/{fid}")
    assert d.json()["deleted"] is True
    g = await client.get(f"/v1/files/{fid}")
    assert g.status_code == 404


async def test_chat_with_attachment(client):
    up = await client.post("/v1/files", files={"file": ("d.txt", b"data", "text/plain")})
    fid = up.json()["id"]
    r = await client.post("/v1/chat/completions", json={
        "model": "agent_default",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "summarize the file"},
            {"type": "file", "file": {"file_id": fid}},
        ]}],
    })
    assert r.status_code == 200
    assert r.json()["choices"][0]["message"]["role"] == "assistant"
