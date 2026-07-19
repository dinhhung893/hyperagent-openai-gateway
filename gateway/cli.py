"""Unified command-line interface: `hyperagent-gateway` (alias `hga`).

Two commands to go live:  hga login   →   hga serve
Other commands: init (write .env), agents (list), doctor (preflight), quickstart.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

from . import __version__


def _set_env(mapping: dict) -> None:
    for k, v in mapping.items():
        if v is not None:
            os.environ[k] = str(v)


# --------------------------------------------------------------------------- #
def cmd_init(args) -> int:
    """Interactive wizard that writes ~/.hyperagent-gateway/.env."""
    home = os.path.expanduser("~/.hyperagent-gateway")
    os.makedirs(home, exist_ok=True)
    path = os.path.join(home, ".env")
    defaults = {
        "GATEWAY_UPSTREAM": "mcp",
        "HYPERAGENT_MCP_URL": "https://hyperagent.com/api/mcp",
        "SHIM_API_KEYS": "sk-local-" + os.urandom(6).hex(),
        "GATEWAY_DEFAULT_AGENT": "",
        "GATEWAY_PORT": "8000",
    }
    values = dict(defaults)
    if not args.yes:
        print("Configure the gateway (.env). Press Enter to accept the default.\n")
        for k, d in defaults.items():
            try:
                entered = input(f"  {k} [{d}]: ").strip()
            except EOFError:
                entered = ""
            if entered:
                values[k] = entered
    lines = [f"{k}={v}" for k, v in values.items() if v != ""]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(path, 0o600)
    print(f"\nWrote {path}")
    print("Next:  hga login   (once)   then   hga serve")
    return 0


def cmd_login(args) -> int:
    from . import oauth
    if args.remote_start:
        url = oauth.remote_start(args.redirect)
        print("Open this URL in a browser, approve, then copy the ?code=… value:\n")
        print(url)
        print("\nFinish with:  hga login --remote-finish --code <CODE> [--state <STATE>]")
        return 0
    if args.remote_finish:
        if not args.code:
            print("error: --code is required with --remote-finish", file=sys.stderr)
            return 2
        out = oauth.remote_finish(args.code, args.state, out=args.out)
        print(f"Token bundle written to {out}")
        return 0
    oauth.login(out=args.out, port=args.port)
    return 0


def cmd_serve(args) -> int:
    _set_env({
        "GATEWAY_HOST": args.host, "GATEWAY_PORT": args.port,
        "GATEWAY_UPSTREAM": args.upstream, "HYPERAGENT_TOKEN_FILE": args.token_file,
        "SHIM_API_KEYS": args.api_keys, "GATEWAY_DEFAULT_AGENT": args.default_agent,
        "GATEWAY_EXEC_MODE": args.exec_mode, "GATEWAY_LOG_LEVEL": args.log_level,
    })
    import uvicorn
    print(f"Serving OpenAI-compatible gateway on http://{args.host}:{args.port}/v1  "
          f"(upstream={os.environ.get('GATEWAY_UPSTREAM', 'mcp')})")
    uvicorn.run("gateway.app:app", host=args.host, port=int(args.port),
                reload=args.reload, log_level=args.log_level)
    return 0


def _make_ctx():
    from .config import Settings
    from .upstream import build_adapter
    settings = Settings()
    return settings, build_adapter(settings)


def cmd_agents(args) -> int:
    settings, adapter = _make_ctx()

    async def run():
        try:
            agents = await adapter.list_agents()
        finally:
            await adapter.aclose()
        if not agents:
            print("No agents found. Create a named agent in Hyperagent, or run with "
                  "GATEWAY_UPSTREAM=mock.")
            return 1
        print(f"{'ID':<28} NAME")
        print("-" * 50)
        for a in agents:
            print(f"{a.id:<28} {a.name}")
        return 0

    return asyncio.run(run())


def cmd_doctor(args) -> int:
    settings, adapter = _make_ctx()
    print(f"upstream        : {settings.upstream}")
    print(f"mcp endpoint    : {settings.mcp_endpoint}")
    print(f"token file      : {settings.token_file} "
          f"({'present' if os.path.exists(os.path.expanduser(settings.token_file)) else 'MISSING'})")
    print(f"client keys     : {'set' if settings.key_set else 'dev mode (any key)'}")

    async def run():
        try:
            agents = await adapter.list_agents()
            print(f"upstream reach  : OK ({len(agents)} agent(s))")
            return 0 if agents else 1
        except Exception as e:
            print(f"upstream reach  : FAILED — {e}")
            return 1
        finally:
            await adapter.aclose()

    code = asyncio.run(run())
    print("\nStatus:", "ready ✓" if code == 0 else "needs attention ✗")
    return code


def cmd_quickstart(args) -> int:
    token = os.path.expanduser(os.environ.get("HYPERAGENT_TOKEN_FILE",
                               "~/.hyperagent-gateway/tokens.json"))
    if args.upstream != "mock" and not os.path.exists(token):
        from . import oauth
        oauth.login()
    return cmd_serve(args)


# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hyperagent-gateway",
                                description="OpenAI-compatible API gateway for Hyperagent.com")
    p.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("init", help="write ~/.hyperagent-gateway/.env")
    pi.add_argument("-y", "--yes", action="store_true", help="accept defaults, no prompts")
    pi.set_defaults(func=cmd_init)

    pl = sub.add_parser("login", help="one-time Hyperagent OAuth")
    pl.add_argument("--out", default=os.path.expanduser("~/.hyperagent-gateway/tokens.json"))
    pl.add_argument("--port", type=int, default=8765, help="local callback port")
    pl.add_argument("--remote-start", action="store_true", help="headless: print authorize URL")
    pl.add_argument("--remote-finish", action="store_true", help="headless: exchange code")
    pl.add_argument("--redirect", default="", help="redirect URI for --remote-start")
    pl.add_argument("--code", default="")
    pl.add_argument("--state", default=None)
    pl.set_defaults(func=cmd_login)

    ps = sub.add_parser("serve", help="run the gateway server")
    ps.add_argument("--host", default=os.environ.get("GATEWAY_HOST", "0.0.0.0"))
    ps.add_argument("--port", default=os.environ.get("GATEWAY_PORT", "8000"))
    ps.add_argument("--upstream", default=os.environ.get("GATEWAY_UPSTREAM", "mcp"),
                    choices=["mcp", "mock"])
    ps.add_argument("--token-file", default=None)
    ps.add_argument("--api-keys", default=None, help="comma-separated client keys")
    ps.add_argument("--default-agent", default=None)
    ps.add_argument("--exec-mode", default=None, choices=[None, "roundtrip", "auto"])
    ps.add_argument("--log-level", default=os.environ.get("GATEWAY_LOG_LEVEL", "info"))
    ps.add_argument("--reload", action="store_true", help="dev auto-reload")
    ps.set_defaults(func=cmd_serve)

    pa = sub.add_parser("agents", help="list your Hyperagent agents")
    pa.set_defaults(func=cmd_agents)

    pd = sub.add_parser("doctor", help="check config + upstream reachability")
    pd.set_defaults(func=cmd_doctor)

    pq = sub.add_parser("quickstart", help="login (if needed) then serve")
    pq.add_argument("--host", default=os.environ.get("GATEWAY_HOST", "0.0.0.0"))
    pq.add_argument("--port", default=os.environ.get("GATEWAY_PORT", "8000"))
    pq.add_argument("--upstream", default=os.environ.get("GATEWAY_UPSTREAM", "mcp"),
                    choices=["mcp", "mock"])
    pq.add_argument("--token-file", default=None)
    pq.add_argument("--api-keys", default=None)
    pq.add_argument("--default-agent", default=None)
    pq.add_argument("--exec-mode", default=None, choices=[None, "roundtrip", "auto"])
    pq.add_argument("--log-level", default="info")
    pq.add_argument("--reload", action="store_true")
    pq.set_defaults(func=cmd_quickstart)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
