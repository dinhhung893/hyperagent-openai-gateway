#!/usr/bin/env python3
"""One-time Hyperagent MCP OAuth login (Authorization Code + PKCE + DCR).

Performs the browser handshake documented in docs/product/upstream-mcp.md and
writes a refresh-capable token bundle the gateway can load and auto-rotate.

Usage:
    python tools/oauth_login.py --out ~/.hyperagent-gateway/tokens.json

Requires a machine with a browser. Discovers OAuth metadata from the issuer,
registers a public client (DCR), runs a localhost redirect listener, exchanges
the code with PKCE, and stores {access_token, refresh_token, expires_at,
client_id, token_endpoint}.
"""
from __future__ import annotations

import argparse
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
REDIRECT_PORT = 8765
REDIRECT_URI = f"http://127.0.0.1:{REDIRECT_PORT}/callback"


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def discover(client: httpx.Client) -> dict:
    r = client.get(f"{ISSUER}/.well-known/oauth-authorization-server")
    r.raise_for_status()
    return r.json()


def register_client(client: httpx.Client, reg_endpoint: str) -> str:
    body = {
        "client_name": "hyperagent-openai-gateway",
        "redirect_uris": [REDIRECT_URI],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
        "scope": SCOPES,
    }
    r = client.post(reg_endpoint, json=body)
    r.raise_for_status()
    return r.json()["client_id"]


class _Handler(http.server.BaseHTTPRequestHandler):
    code_holder: dict = {}

    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404); self.end_headers(); return
        qs = urllib.parse.parse_qs(parsed.query)
        _Handler.code_holder["code"] = qs.get("code", [None])[0]
        _Handler.code_holder["state"] = qs.get("state", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h3>Authorized. You can close this tab and return to the terminal.</h3>")

    def log_message(self, *_):  # silence
        return


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.expanduser("~/.hyperagent-gateway/tokens.json"))
    args = ap.parse_args()

    with httpx.Client(timeout=30.0) as client:
        meta = discover(client)
        auth_ep = meta["authorization_endpoint"]
        token_ep = meta["token_endpoint"]
        reg_ep = meta.get("registration_endpoint")
        client_id = register_client(client, reg_ep) if reg_ep else "hyperagent-openai-gateway"

        verifier = _b64url(secrets.token_bytes(48))
        challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
        state = secrets.token_urlsafe(16)

        params = {
            "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT_URI,
            "scope": SCOPES, "state": state,
            "code_challenge": challenge, "code_challenge_method": "S256",
        }
        url = auth_ep + "?" + urllib.parse.urlencode(params)

        server = http.server.HTTPServer(("127.0.0.1", REDIRECT_PORT), _Handler)
        threading.Thread(target=server.handle_request, daemon=True).start()

        print("Opening browser for Hyperagent sign-in...\nIf it doesn't open, visit:\n", url)
        webbrowser.open(url)

        while "code" not in _Handler.code_holder:
            time.sleep(0.2)
        if _Handler.code_holder.get("state") != state:
            raise SystemExit("state mismatch; aborting")
        code = _Handler.code_holder["code"]
        if not code:
            raise SystemExit("no authorization code received")

        tok = client.post(token_ep, data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI,
            "client_id": client_id, "code_verifier": verifier,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        tok.raise_for_status()
        payload = tok.json()

        bundle = {
            "access_token": payload["access_token"],
            "refresh_token": payload.get("refresh_token"),
            "expires_at": time.time() + int(payload.get("expires_in", 3600)),
            "client_id": client_id,
            "token_endpoint": token_ep,
        }
        os.makedirs(os.path.dirname(os.path.expanduser(args.out)) or ".", exist_ok=True)
        with open(os.path.expanduser(args.out), "w") as f:
            json.dump(bundle, f, indent=2)
        os.chmod(os.path.expanduser(args.out), 0o600)
        print(f"\nToken bundle written to {args.out}")
        print("Refresh token present:", bool(bundle["refresh_token"]))


if __name__ == "__main__":
    main()
