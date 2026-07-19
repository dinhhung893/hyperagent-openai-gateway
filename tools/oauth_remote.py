#!/usr/bin/env python3
"""Two-step Hyperagent OAuth for remote/handoff flows (no local listener).

Unlike tools/oauth_login.py (localhost listener), this variant supports flows
where the browser runs elsewhere: step `start` registers a client (DCR) with a
provided redirect_uri, generates PKCE + state, persists the session, and prints
the authorize URL. Step `finish` takes the authorization code (or the full
callback URL) and exchanges it for tokens.

Usage:
  python3.11 tools/oauth_remote.py start --redirect <url> [--session PATH]
  python3.11 tools/oauth_remote.py finish --code <code> [--state <state>]
  python3.11 tools/oauth_remote.py finish --callback-url "<url-with-?code=...>"
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import time
import urllib.parse

import httpx

ISSUER = "https://hyperagent.com"
SCOPES = "threads:read threads:write approvals:read approvals:write offline_access"
DEFAULT_SESSION = os.path.expanduser("~/.hyperagent-gateway/oauth-session.json")
DEFAULT_OUT = os.path.expanduser("~/.hyperagent-gateway/tokens.json")


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _write_json(path: str, data: dict, mode: int = 0o600) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    os.chmod(path, mode)


def start(args) -> None:
    with httpx.Client(timeout=30.0) as client:
        meta = client.get(f"{ISSUER}/.well-known/oauth-authorization-server")
        meta.raise_for_status()
        meta = meta.json()

        reg = client.post(meta["registration_endpoint"], json={
            "client_name": "hyperagent-openai-gateway",
            "redirect_uris": [args.redirect],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "scope": SCOPES,
        })
        reg.raise_for_status()
        client_id = reg.json()["client_id"]

        verifier = _b64url(secrets.token_bytes(48))
        challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
        state = secrets.token_urlsafe(16)

        url = meta["authorization_endpoint"] + "?" + urllib.parse.urlencode({
            "response_type": "code", "client_id": client_id, "redirect_uri": args.redirect,
            "scope": SCOPES, "state": state,
            "code_challenge": challenge, "code_challenge_method": "S256",
        })

        _write_json(args.session, {
            "client_id": client_id, "verifier": verifier, "state": state,
            "redirect_uri": args.redirect, "token_endpoint": meta["token_endpoint"],
            "created_at": time.time(),
        })
        print("SESSION_SAVED", args.session)
        print("AUTHORIZE_URL", url)


def finish(args) -> None:
    with open(args.session) as f:
        sess = json.load(f)

    code, state = args.code, args.state
    if args.callback_url:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(args.callback_url).query)
        code = (q.get("code") or [None])[0]
        state = (q.get("state") or [None])[0]
    if not code:
        sys.exit("error: no authorization code provided")
    if state is not None and state != sess["state"]:
        sys.exit(f"error: state mismatch (got {state!r})")

    with httpx.Client(timeout=30.0) as client:
        tok = client.post(sess["token_endpoint"], data={
            "grant_type": "authorization_code", "code": code,
            "redirect_uri": sess["redirect_uri"], "client_id": sess["client_id"],
            "code_verifier": sess["verifier"],
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        if tok.status_code >= 400:
            sys.exit(f"error: token exchange failed {tok.status_code}: {tok.text[:400]}")
        payload = tok.json()

    _write_json(args.out, {
        "access_token": payload["access_token"],
        "refresh_token": payload.get("refresh_token"),
        "expires_at": time.time() + int(payload.get("expires_in", 3600)),
        "client_id": sess["client_id"],
        "token_endpoint": sess["token_endpoint"],
    })
    print("TOKENS_WRITTEN", args.out)
    print("HAS_REFRESH", bool(payload.get("refresh_token")))
    print("SCOPE", payload.get("scope", "(not reported)"))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--redirect", required=True)
    s.add_argument("--session", default=DEFAULT_SESSION)
    s.set_defaults(fn=start)
    f = sub.add_parser("finish")
    f.add_argument("--code")
    f.add_argument("--state")
    f.add_argument("--callback-url")
    f.add_argument("--session", default=DEFAULT_SESSION)
    f.add_argument("--out", default=DEFAULT_OUT)
    f.set_defaults(fn=finish)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
