"""Hyperagent MCP OAuth helpers (packaged so the CLI works after install).

login(): one-time browser flow with a localhost listener (Authorization Code +
PKCE + Dynamic Client Registration), writes a refresh-capable token bundle.
remote_start()/remote_finish(): two-step flow for headless servers.
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import threading
import time
import urllib.parse
import webbrowser

import httpx

ISSUER = "https://hyperagent.com"
SCOPES = "threads:read threads:write approvals:read approvals:write offline_access"
DEFAULT_OUT = os.path.expanduser("~/.hyperagent-gateway/tokens.json")
DEFAULT_SESSION = os.path.expanduser("~/.hyperagent-gateway/oauth-session.json")


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(os.path.expanduser(path)) or ".", exist_ok=True)
    with open(os.path.expanduser(path), "w") as f:
        json.dump(data, f, indent=2)
    os.chmod(os.path.expanduser(path), 0o600)


def _discover(client: httpx.Client) -> dict:
    r = client.get(f"{ISSUER}/.well-known/oauth-authorization-server")
    r.raise_for_status()
    return r.json()


def _register(client: httpx.Client, reg_endpoint: str, redirect_uri: str) -> str:
    r = client.post(reg_endpoint, json={
        "client_name": "hyperagent-openai-gateway",
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
        "scope": SCOPES,
    })
    r.raise_for_status()
    return r.json()["client_id"]


def _authorize_url(meta: dict, client_id: str, redirect_uri: str, state: str,
                   challenge: str) -> str:
    return meta["authorization_endpoint"] + "?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": client_id, "redirect_uri": redirect_uri,
        "scope": SCOPES, "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
    })


def _exchange(client: httpx.Client, token_endpoint: str, code: str, redirect_uri: str,
              client_id: str, verifier: str) -> dict:
    r = client.post(token_endpoint, data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
        "client_id": client_id, "code_verifier": verifier,
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    r.raise_for_status()
    return r.json()


def _bundle(payload: dict, client_id: str, token_endpoint: str) -> dict:
    return {
        "access_token": payload["access_token"],
        "refresh_token": payload.get("refresh_token"),
        "expires_at": time.time() + int(payload.get("expires_in", 3600)),
        "client_id": client_id,
        "token_endpoint": token_endpoint,
    }


def login(out: str = DEFAULT_OUT, port: int = 8765) -> str:
    """Interactive browser login. Returns the path to the written token bundle."""
    redirect_uri = f"http://127.0.0.1:{port}/callback"
    holder: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            holder["code"] = q.get("code", [None])[0]
            holder["state"] = q.get("state", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h3>Authorized. Return to your terminal.</h3>")

        def log_message(self, *_):
            return

    with httpx.Client(timeout=30.0) as client:
        meta = _discover(client)
        client_id = _register(client, meta["registration_endpoint"], redirect_uri) \
            if meta.get("registration_endpoint") else "hyperagent-openai-gateway"
        verifier = _b64url(secrets.token_bytes(48))
        challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
        state = secrets.token_urlsafe(16)
        url = _authorize_url(meta, client_id, redirect_uri, state, challenge)

        server = http.server.HTTPServer(("127.0.0.1", port), Handler)
        threading.Thread(target=server.handle_request, daemon=True).start()
        print("Opening browser for Hyperagent sign-in…\nIf it doesn't open, visit:\n", url)
        webbrowser.open(url)
        while "code" not in holder:
            time.sleep(0.2)
        if holder.get("state") != state:
            raise SystemExit("state mismatch; aborting")
        if not holder.get("code"):
            raise SystemExit("no authorization code received")
        payload = _exchange(client, meta["token_endpoint"], holder["code"], redirect_uri,
                            client_id, verifier)
        _write_json(out, _bundle(payload, client_id, meta["token_endpoint"]))
    print(f"Token bundle written to {out}")
    return out


def remote_start(redirect_uri: str, session: str = DEFAULT_SESSION) -> str:
    """Headless step 1: register + PKCE, persist session, return authorize URL."""
    with httpx.Client(timeout=30.0) as client:
        meta = _discover(client)
        client_id = _register(client, meta["registration_endpoint"], redirect_uri)
        verifier = _b64url(secrets.token_bytes(48))
        challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
        state = secrets.token_urlsafe(16)
        _write_json(session, {"client_id": client_id, "verifier": verifier, "state": state,
                              "redirect_uri": redirect_uri, "token_endpoint": meta["token_endpoint"]})
        return _authorize_url(meta, client_id, redirect_uri, state, challenge)


def remote_finish(code: str, state: str | None = None, session: str = DEFAULT_SESSION,
                  out: str = DEFAULT_OUT) -> str:
    """Headless step 2: exchange the code for tokens."""
    with open(os.path.expanduser(session)) as f:
        sess = json.load(f)
    if state is not None and state != sess["state"]:
        raise SystemExit("state mismatch")
    with httpx.Client(timeout=30.0) as client:
        payload = _exchange(client, sess["token_endpoint"], code, sess["redirect_uri"],
                            sess["client_id"], sess["verifier"])
    _write_json(out, _bundle(payload, sess["client_id"], sess["token_endpoint"]))
    return out
