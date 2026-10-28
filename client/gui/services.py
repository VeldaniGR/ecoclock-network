"""Servicios de la GUI (logica pura, sin PyQt6). Cada funcion envuelve un sub-comando del CLI para que la UI solo tenga que llamar a algo simple.
Asi los tests no necesitan PyQt6 instalado. """
from __future__ import annotations

import json
import requests
from typing import Any
from client import cli


def login(base_url: str, username: str, password: str) -> dict[str, Any]:
    """Hace login y devuelve el body (access_token + refresh_token)."""
    import argparse
    args = argparse.Namespace(
        base_url=base_url, username=username, password=password,
    )
    return cli.cmd_login(args)


def next_task(base_url: str, token: str | None = None) -> dict[str, Any]:
    """Pide la siguiente tarea (con auto-refresh en 401)."""
    import argparse
    args = argparse.Namespace(base_url=base_url, token=token)
    return cli.cmd_next(args)


def submit_task(
    base_url: str,
    token: str | None,
    task_id: int,
    output: dict,
    compute_time_sec: float,
    client: str = "gui",
    client_mode: str = "manual",
) -> dict[str, Any]:
    """Envia el resultado de una tarea (con auto-refresh en 401)."""
    import argparse
    args = argparse.Namespace(
        base_url=base_url,
        token=token,
        task_id=task_id,
        output=json.dumps(output),
        compute_time_sec=compute_time_sec,
        client=client,
        client_mode=client_mode,
    )
    return cli.cmd_submit(args)


def me(base_url: str, token: str | None = None) -> dict[str, Any]:
    """Devuelve los créditos del usuario (GET /me/credits) con auto-refresh."""
    r = cli.authenticated_get(base_url, "/me/credits", token=token)
    r.raise_for_status()
    return r.json()


def register(base_url: str, username: str, email: str, password: str) -> dict[str, Any]:
    """Registra un nuevo usuario."""
    import argparse
    args = argparse.Namespace(
        base_url=base_url, username=username, email=email, password=password,
    )
    return cli.cmd_register(args)


# ──────────────────────────────────────────────────────────────
# Nodos Ciudadanos
# ──────────────────────────────────────────────────────────────

def get_my_node(base_url: str, token: str | None = None) -> dict[str, Any] | None:
    """GET /nodes/me. Devuelve None si 404."""
    r = cli.authenticated_get(base_url, "/nodes/me", token=token)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def list_public_nodes(base_url: str, token: str | None = None) -> list[dict[str, Any]]:
    """GET /nodes"""
    r = cli.authenticated_get(base_url, "/nodes", token=token)
    r.raise_for_status()
    return r.json()


def create_node(base_url: str, name: str, token: str | None = None) -> dict[str, Any]:
    """POST /nodes"""
    r = cli.authenticated_post(
        base_url, "/nodes", token=token, json={"name": name}
    )
    r.raise_for_status()
    return r.json()


def join_node_by_code(base_url: str, code: str, token: str | None = None) -> dict[str, Any]:
    """POST /nodes/join/{code}"""
    r = cli.authenticated_post(
        base_url, f"/nodes/join/{code}", token=token
    )
    r.raise_for_status()
    return r.json()


def leave_node(base_url: str, token: str | None = None) -> dict[str, Any]:
    """POST /nodes/leave"""
    r = cli.authenticated_post(base_url, "/nodes/leave", token=token)
    r.raise_for_status()
    return r.json() if r.content else {"detail": "ok"}


def delete_node(base_url: str, node_id: int, token: str | None = None) -> dict[str, Any]:
    """DELETE /nodes/{id}"""
    r = cli.authenticated_request(
        "DELETE", base_url, f"/nodes/{node_id}", token=token
    )
    r.raise_for_status()
    return r.json() if r.content else {"detail": "ok"}


def request_join_node(base_url: str, node_id: int, token: str | None = None) -> dict[str, Any]:
    """POST /nodes/{id}/request"""
    r = cli.authenticated_post(
        base_url, f"/nodes/{node_id}/request", token=token
    )
    r.raise_for_status()
    return r.json() if r.content else {"detail": "ok"}


# ──────────────────────────────────────────────────────────────
# Nodos Ciudadanos
# ──────────────────────────────────────────────────────────────

def get_my_node(base_url: str, token: str | None = None) -> dict[str, Any] | None:
    r = cli.authenticated_get(base_url, "/nodes/me", token=token)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def list_public_nodes(base_url: str, token: str | None = None) -> list[dict[str, Any]]:
    r = cli.authenticated_get(base_url, "/nodes", token=token)
    r.raise_for_status()
    return r.json()


def create_node(base_url: str, name: str, token: str | None = None) -> dict[str, Any]:
    r = cli.authenticated_post(base_url, "/nodes", token=token, json={"name": name})
    r.raise_for_status()
    return r.json()


def join_node_by_code(base_url: str, code: str, token: str | None = None) -> dict[str, Any]:
    r = cli.authenticated_post(base_url, f"/nodes/join/{code}", token=token)
    r.raise_for_status()
    return r.json()


def leave_node(base_url: str, token: str | None = None) -> dict[str, Any]:
    r = cli.authenticated_post(base_url, "/nodes/leave", token=token)
    r.raise_for_status()
    return r.json() if r.content else {"detail": "ok"}


def delete_node(base_url: str, node_id: int, token: str | None = None) -> dict[str, Any]:
    r = cli.authenticated_request("DELETE", base_url, f"/nodes/{node_id}", token=token)
    r.raise_for_status()
    return r.json() if r.content else {"detail": "ok"}


def request_join_node(base_url: str, node_id: int, token: str | None = None) -> dict[str, Any]:
    r = cli.authenticated_post(base_url, f"/nodes/{node_id}/request", token=token)
    r.raise_for_status()
    return r.json() if r.content else {"detail": "ok"}
