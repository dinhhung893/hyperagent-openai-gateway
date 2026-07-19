"""Smoke tests for the unified CLI (hyperagent-gateway / hga)."""
import pytest

from gateway import cli


def test_version_exits_zero():
    with pytest.raises(SystemExit) as e:
        cli.main(["--version"])
    assert e.value.code == 0


def test_parser_serve_flags():
    args = cli.build_parser().parse_args(["serve", "--port", "1234", "--upstream", "mock"])
    assert args.command == "serve" and args.port == "1234" and args.upstream == "mock"
    assert args.func is cli.cmd_serve


def test_parser_has_all_subcommands():
    names = set()
    # argparse subparsers: introspect via parse of --help would exit; instead parse each
    for cmd in ["init", "login", "serve", "agents", "doctor", "quickstart"]:
        args = cli.build_parser().parse_args([cmd] if cmd != "login" else ["login"])
        names.add(args.command)
    assert {"init", "login", "serve", "agents", "doctor", "quickstart"} <= names


def test_agents_against_mock(monkeypatch, capsys):
    monkeypatch.setenv("GATEWAY_UPSTREAM", "mock")
    monkeypatch.setenv("SHIM_API_KEYS", "")
    rc = cli.main(["agents"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "agent_default" in out


def test_doctor_against_mock(monkeypatch, capsys):
    monkeypatch.setenv("GATEWAY_UPSTREAM", "mock")
    rc = cli.main(["doctor"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ready" in out and "upstream" in out
