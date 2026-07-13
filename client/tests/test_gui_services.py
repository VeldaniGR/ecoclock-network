"""Tests de los servicios de la GUI (logica pura, sin PyQt6). Mockeamos los sub-comandos del CLI para no depender del server real."""
from __future__ import annotations

from unittest.mock import patch

from client.gui import services


def test_login_devuelve_token():
	fake_response = {"access_token": "abc123", "token_type": "bearer"}
	with patch("client.cli.cmd_login", return_value=fake_response) as m:
		result = services.login("http://x", "user", "testpass")
	assert result == fake_response
	m.assert_called_once()
	args = m.call_args[0][0]
	assert args.base_url == "http://x"
	assert args.username == "user"
	assert args.password == "testpass"


def test_me_pasa_el_token():
	fake_user = {"id": 7, "username": "alice"}
	with patch("client.cli.cmd_me", return_value=fake_user) as m:
		result = services.me("http://x", "fake-token-123")
	assert result == fake_user
	m.assert_called_once()
	assert m.call_args[0][0].token == "fake-token-123"


def test_next_task_pide_al_server():
	fake_task = {"id": 42, "name": "ndvi-dummy", "status": "assigned"}
	with patch("client.cli.cmd_next", return_value=fake_task) as m:
		result = services.next_task("http://x", "fake-token-123")
	assert result == fake_task
	m.assert_called_once()
	assert m.call_args[0][0].token == "fake-token-123"


def test_submit_task_serializa_output_a_json():
	fake_resp = {"id": 1, "task_id": 42, "status": None}
	with patch("client.cli.cmd_submit", return_value=fake_resp) as m:
		result = services.submit_task(
			"http://x", "fake-token-123", 42, {"ndvi": 0.65}, 1.23
		)
	assert result == fake_resp
	m.assert_called_once()
	args = m.call_args[0][0]
	assert args.task_id == 42
	assert args.compute_time_sec == 1.23
	# El output debe serializarse como JSON string (lo que espera el server)
	import json
	assert json.loads(args.output) == {"ndvi": 0.65}
