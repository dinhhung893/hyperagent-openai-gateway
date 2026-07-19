"""E10: multi-tenant identities via GATEWAY_KEYS_FILE — auth + per-key policy."""
import json
import os
import tempfile

import httpx
import pytest

from tests.conftest import make_app


async def _client_for(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_multitenant_auth_and_policy():
    d = tempfile.mkdtemp()
    kf = os.path.join(d, "keys.json")
    with open(kf, "w") as f:
        json.dump([
            {"api_key": "kA", "token_file": os.path.join(d, "a.json"),
             "disabled_tools": ["shell", "write_file"], "label": "restricted"},
            {"api_key": "kB", "token_file": os.path.join(d, "b.json"), "label": "full"},
        ], f)
    os.environ["GATEWAY_KEYS_FILE"] = kf
    try:
        app = make_app()
        async with app.router.lifespan_context(app):
            c = await _client_for(app)

            # unknown key rejected
            r = await c.get("/v1/models", headers={"authorization": "Bearer nope"})
            assert r.status_code == 401

            # known keys accepted
            assert (await c.get("/v1/models", headers={"authorization": "Bearer kA"})).status_code == 200
            assert (await c.get("/v1/models", headers={"authorization": "Bearer kB"})).status_code == 200

            # per-key tool policy: kA hides shell/write_file, kB shows them
            na = {t["function"]["name"] for t in
                  (await c.get("/v1/tools", headers={"authorization": "Bearer kA"})).json()["data"]}
            nb = {t["function"]["name"] for t in
                  (await c.get("/v1/tools", headers={"authorization": "Bearer kB"})).json()["data"]}
            assert "shell" not in na and "write_file" not in na and "web_search" in na
            assert "shell" in nb

            # kA cannot force a disabled tool
            r = await c.post("/v1/chat/completions", headers={"authorization": "Bearer kA"}, json={
                "model": "agent_default", "messages": [{"role": "user", "content": "ls"}],
                "tool_choice": {"type": "function", "function": {"name": "shell"}}})
            assert r.status_code == 400 and r.json()["error"]["code"] == "tool_disabled"

            # kB can (roundtrip tool_call)
            r = await c.post("/v1/chat/completions", headers={"authorization": "Bearer kB"}, json={
                "model": "agent_default", "messages": [{"role": "user", "content": "ls"}],
                "tool_choice": {"type": "function", "function": {"name": "shell"}}})
            assert r.status_code == 200
            assert r.json()["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "shell"
            await c.aclose()
    finally:
        os.environ.pop("GATEWAY_KEYS_FILE", None)
