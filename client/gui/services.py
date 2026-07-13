"""Servicios de la GUI (logica pura, sin PyQt6). Cada funcion envuelve un sub-comando del CLI para que la UI solo tenga que llamar a algo simple.
Asi los tests no necesitan PyQt6 instalado. """
from __future__ import annotations

import json
from typing import Any
from client import cli

def login(base_url: str, username: str, password: str) -> dict[str, Any]:
	"""Hace login y devuelve el body de la respuesta (incluye access_token)."""
	import argparse
	args = argparse.Namespace(
		base_url=base_url, username=username, password=password,
	)
	return cli.cmd_login(args)


def next_task(base_url: str, token: str) -> dict[str, Any]:
	"""Pide la siguiente tarea al servidor."""
	import argparse
	args = argparse.Namespace(base_url=base_url, token=token)
	return cli.cmd_next(args)


def submit_task(
	base_url: str, token: str, task_id: int, output: dict, compute_time_sec: float,
	) -> dict[str, Any]:
	"""Envia el resultado de una tarea."""
	import argparse
	args = argparse.Namespace(
		base_url=base_url, token=token, task_id=task_id,
		output=json.dumps(output), compute_time_sec=compute_time_sec,
	)
	return cli.cmd_submit(args)


def me(base_url: str, token: str) -> dict[str, Any]:
	"""Devuelve los datos del usuario autenticado."""
	import argparse
	args = argparse.Namespace(base_url=base_url, token=token)
	return cli.cmd_me(args)
