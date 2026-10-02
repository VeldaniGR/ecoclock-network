"""Tests del CLI cliente (Fase 1).

Unit tests: mockean `requests` y el token store, corren en cualquier sitio.
Integration tests: golpean el server real. Skipped por defecto. Para correrlos:
    ECOCLOCK_RUN_INTEGRATION=1 pytest -m integration
o:
    pytest -m integration  (con `docker compose up -d` ya levantado)
"""
from __future__ import annotations

import argparse
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from client import cli
from client.cli import (
    CLIError,
    build_parser,
    cmd_register,
    cmd_login,
    cmd_me,
    cmd_next,
    cmd_submit,
    cmd_run,
    cmd_logout,
)


def _ns(**kwargs):
    kwargs.setdefault("base_url", os.environ.get("ECOCLOCK_BASE_URL", "http://127.0.0.1:8000"))
    return argparse.Namespace(**kwargs)


def _mock_response(status_code=200, json_data=None, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.json = MagicMock(return_value=json_data if json_data is not None else {})
    r.text = text or json.dumps(json_data or {})
    return r


# --- Token store -------------------------------------------------------------

def test_token_path_uses_xdg_when_set(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    p = cli._token_path()
    assert p == tmp_path / "ecoclock" / "token.json"


def test_token_path_falls_back_to_home_config(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    p = cli._token_path()
    assert p == tmp_path / ".config" / "ecoclock" / "token.json"


def test_save_and_load_token(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cli.save_token("tok-1234567890")
    assert cli.load_token() == "tok-1234567890"
    assert (tmp_path / "ecoclock" / "token.json").exists()


def test_load_token_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert cli.load_token() is None


def test_clear_token(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cli.save_token("zzz")
    cli.clear_token()
    assert cli.load_token() is None


# --- Sub-comandos (unit, con requests mockeado) -----------------------------

def test_cmd_register_ok():
    body = {"id": 1, "email": "a@b.c", "username": "u"}
    with patch.object(cli.requests, "post", return_value=_mock_response(201, body)):
        out = cmd_register(_ns(email="a@b.c", username="u", password="***"))
    assert out == body


def test_cmd_register_400_raises():
    with patch.object(cli.requests, "post", return_value=_mock_response(400, {"detail": "dup"})):
        with pytest.raises(CLIError):
            cmd_register(_ns(email="a@b.c", username="u", password="***"))


def test_cmd_login_saves_token(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    body = {"access_token": "tok-1234567890", "token_type": "bearer"}
    with patch.object(cli.requests, "post", return_value=_mock_response(200, body)):
        out = cmd_login(_ns(username="u", password="***"))
    assert out == body
    assert cli.load_token() == "tok-1234567890"


def test_cmd_login_no_token_raises():
    with patch.object(cli.requests, "post", return_value=_mock_response(200, {"foo": "bar"})):
        with pytest.raises(CLIError):
            cmd_login(_ns(username="u", password="***"))


def test_cmd_me_requires_token(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    with pytest.raises(CLIError):
        cmd_me(_ns(token=None))


def test_cmd_me_ok():
    body = {"id": 1, "username": "u", "email": "a@b.c"}
    with patch.object(cli.requests, "get", return_value=_mock_response(200, body)):
        out = cmd_me(_ns(token="t"))
    assert out == body


def test_cmd_next_ok():
    body = {"id": 42, "name": "ndvi-dummy", "status": "assigned"}
    with patch.object(cli.requests, "get", return_value=_mock_response(200, body)):
        out = cmd_next(_ns(token="t"))
    assert out["id"] == 42


def test_cmd_submit_ok():
    body = {"task_id": 42, "output": {"ndvi": 0.5}, "status": "done"}
    with patch.object(cli.requests, "post", return_value=_mock_response(201, body)):
        out = cmd_submit(_ns(token="t", task_id=42, output='{"ndvi": 0.5}', compute_time_sec=0.1))
    assert out["task_id"] == 42


# --- run() flujo completo (unit) --------------------------------------------

def test_cmd_run_full_flow(tmp_path, monkeypatch):
    """Flujo: login -> next -> submit. _auth hace login (no hay token, no --register)."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    login_body = {"access_token": "***", "token_type": "bearer"}
    next_body = {"id": 7, "name": "ndvi-dummy", "status": "assigned"}
    submit_body = {"task_id": 7, "output": {"ndvi": 0.5}, "status": "done"}

    # POST: login (200), submit (201)
    post_responses = [
        _mock_response(200, login_body),   # login
        _mock_response(201, submit_body),  # submit
    ]
    # GET: next (200)
    get_response = _mock_response(200, next_body)

    with patch.object(cli.requests, "post", side_effect=post_responses), \
         patch.object(cli.requests, "get", return_value=get_response):
        out = cmd_run(_ns(
            email="a@b.c", username="u", password="***",
            register=False, login=True, force_register=False, token=None
        ))
    assert out["task_id"] == 7
    assert out["status"] == "done"


def test_cmd_run_register_then_login_fallback(tmp_path, monkeypatch):
    """Si register falla por 400 (duplicado) y --login está activo, cae a login."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    login_body = {"access_token": "***", "token_type": "bearer"}
    next_body = {"id": 8, "name": "x", "status": "assigned"}
    submit_body = {"task_id": 8, "output": {"ndvi": 0.7}, "status": "done"}

    # POST: register (400), login (200), submit (201)
    post_responses = [
        _mock_response(400, {"detail": "duplicate"}),  # register fail
        _mock_response(200, login_body),               # login
        _mock_response(201, submit_body),              # submit
    ]
    get_response = _mock_response(200, next_body)

    with patch.object(cli.requests, "post", side_effect=post_responses), \
         patch.object(cli.requests, "get", return_value=get_response):
        out = cmd_run(_ns(
            email="a@b.c", username="u", password="***",
            register=True, login=True, force_register=True, token=None
        ))
    assert out["task_id"] == 8


# --- Argparse ---------------------------------------------------------------

def test_build_parser_subcommands():
    p = build_parser()
    args = p.parse_args(["register", "--email", "a", "--username", "u", "--password", "p"])
    assert args.command == "register"
    assert args.email == "a"


def test_logout_clears_token(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cli.save_token("t")
    out = cmd_logout(_ns())
    assert out["ok"] is True
    assert cli.load_token() is None


# --- Integration (skipped por defecto si Docker no está arriba) -------------

@pytest.mark.integration
def test_integration_health():
    import httpx
    r = httpx.get("http://127.0.0.1:8000/health", timeout=5.0)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.integration
def test_integration_run_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    suffix = os.urandom(4).hex()
    ns = _ns(
        email=f"cli-it-{suffix}@example.com",
        username=f"cli-it-{suffix}",
        password=f"pw-{suffix}",
        register=True, login=True, force_register=True, token=None
    )
    out = cmd_run(ns)
    assert "task_id" in out
