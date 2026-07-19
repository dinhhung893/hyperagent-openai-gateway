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
    """Set env vars for the values the user actually provided (skip None), so CLI
    flags override, but absent flags leave env/.env/defaults intact."""
    for k, v in mapping.items():
        if v is not None:
            os.environ[k] = str(v)


def _make_ctx(args=None):
    """Build (settings, adapter) honoring --upstream/--token-file when provided."""
    from .config import load_env_files
    load_env_files()  # ensure .env is applied before reading settings
    if args is not None:
        if getattr(args, "upstream", None):
            os.environ["GATEWAY_UPSTREAM"] = args.upstream
        if getattr(args, "token_file", None):
            os.environ["HYPERAGENT_TOKEN_FILE"] = args.token_file
    from .config import Settings
    from .upstream import build_adapter
    settings = Settings()
    return settings, build_adapter(settings)


def _upstream_error(e: Exception, settings) -> None:
    print(f"Could not reach the Hyperagent upstream (upstream={settings.upstream}).",
          file=sys.stderr)
    print(f"  {e}", file=sys.stderr)
    if settings.upstream == "mcp":
        print("Hint: run 'hga login' first, or try offline with '--upstream mock'.",
              file=sys.stderr)


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
    from .config import load_env_files
    load_env_files()  # honor .env; CLI flags below still take precedence
    _set_env({
        "GATEWAY_HOST": args.host, "GATEWAY_PORT": args.port,
        "GATEWAY_UPSTREAM": args.upstream, "HYPERAGENT_TOKEN_FILE": args.token_file,
        "SHIM_API_KEYS": args.api_keys, "GATEWAY_DEFAULT_AGENT": args.default_agent,
        "GATEWAY_EXEC_MODE": args.exec_mode, "GATEWAY_LOG_LEVEL": args.log_level,
    })
    host = os.environ.get("GATEWAY_HOST", "0.0.0.0")
    port = int(os.environ.get("GATEWAY_PORT", "8000"))
    log_level = os.environ.get("GATEWAY_LOG_LEVEL", "info")
    upstream = os.environ.get("GATEWAY_UPSTREAM", "mcp")
    import uvicorn
    print(f"Serving OpenAI-compatible gateway on http://{host}:{port}/v1  (upstream={upstream})")
    uvicorn.run("gateway.app:app", host=host, port=port, reload=bool(args.reload),
                log_level=log_level)
    return 0


def cmd_agents(args) -> int:
    settings, adapter = _make_ctx(args)

    async def run():
        try:
            agents = await adapter.list_agents()
        except Exception as e:  # no ugly traceback for expected conditions
            _upstream_error(e, settings)
            return 1
        finally:
            await adapter.aclose()
        if not agents:
            print("No agents found. Create a named agent in Hyperagent "
                  "(or try '--upstream mock').")
            return 1
        print(f"{'ID':<28} NAME")
        print("-" * 50)
        for a in agents:
            print(f"{a.id:<28} {a.name}")
        return 0

    return asyncio.run(run())


def cmd_doctor(args) -> int:
    settings, adapter = _make_ctx(args)
    print(f"upstream        : {settings.upstream}")
    print(f"mcp endpoint    : {settings.mcp_endpoint}")
    tok = os.path.exists(os.path.expanduser(settings.token_file))
    print(f"token file      : {settings.token_file} ({'present' if tok else 'MISSING'})")
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
    if code != 0 and settings.upstream == "mcp":
        print("Hint: run 'hga login' first, or try offline with '--upstream mock'.")
    return code


def cmd_quickstart(args) -> int:
    from .config import load_env_files
    load_env_files()
    upstream = args.upstream or os.environ.get("GATEWAY_UPSTREAM", "mcp")
    token = os.path.expanduser(args.token_file
                               or os.environ.get("HYPERAGENT_TOKEN_FILE",
                                                 "~/.hyperagent-gateway/tokens.json"))
    if upstream != "mock" and not os.path.exists(token):
        from . import oauth
        oauth.login()
    return cmd_serve(args)


# --------------------------------------------------------------------------- #
def _add_serve_flags(p) -> None:
    p.add_argument("--host", default=None)
    p.add_argument("--port", default=None)
    p.add_argument("--upstream", default=None, choices=["mcp", "mock"])
    p.add_argument("--token-file", default=None)
    p.add_argument("--api-keys", default=None, help="comma-separated client keys")
    p.add_argument("--default-agent", default=None)
    p.add_argument("--exec-mode", default=None, choices=["roundtrip", "auto"])
    p.add_argument("--log-level", default=None)
    p.add_argument("--reload", action="store_true", help="dev auto-reload")


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
    _add_serve_flags(ps)
    ps.set_defaults(func=cmd_serve)

    pa = sub.add_parser("agents", help="list your Hyperagent agents")
    pa.add_argument("--upstream", default=None, choices=["mcp", "mock"])
    pa.add_argument("--token-file", default=None)
    pa.set_defaults(func=cmd_agents)

    pd = sub.add_parser("doctor", help="check config + upstream reachability")
    pd.add_argument("--upstream", default=None, choices=["mcp", "mock"])
    pd.add_argument("--token-file", default=None)
    pd.set_defaults(func=cmd_doctor)

    pq = sub.add_parser("quickstart", help="login (if needed) then serve")
    _add_serve_flags(pq)
    pq.set_defaults(func=cmd_quickstart)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
