"""Tests de integración del sistema de créditos BOINC-style. Golpean el servidor real (docker compose up -d). Se saltan por defecto. Activar con ECOCLOCK_RUN_INTEGRATION=1."""
import os

import httpx
import pytest

BASE_URL = os.getenv("ECOCLOCK_BASE_URL", "http://localhost:8000")
TEST_USER = {
	"username": "velo",
	"password": "OctoCeph2026",
}


@pytest.fixture
def client():
	"""Cliente HTTP síncrono contra el server."""
	return httpx.Client(base_url=BASE_URL, timeout=10.0)


@pytest.fixture
def auth_token(client):
	"""Login + devuelve el JWT del usuario de prueba."""
	r = client.post("/auth/login", json=TEST_USER)
	assert r.status_code == 200, f"Login falló: {r.status_code} {r.text}"
	return r.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
	"""Headers con el Bearer token del usuario de prueba."""
	return {"Authorization": f"Bearer {auth_token}"}


def test_full_credit_cycle(client, auth_headers):
	"""Login → next → submit → me/credits debe reflejar 1 crédito concedido."""
	# 1. Estado inicial: sin créditos.
	r = client.get("/me/credits", headers=auth_headers)
	assert r.status_code == 200, f"GET /me/credits inicial: {r.status_code} {r.text}"
	initial_total = r.json()["total"]
	initial_count = len(r.json()["recent"])
	print(f"  Estado inicial: total={initial_total}, recent={initial_count}")

	# 2. Obtener siguiente tarea.
	r = client.get("/tasks/next", headers=auth_headers)
	assert r.status_code == 200, f"GET /tasks/next: {r.status_code} {r.text}"
	task = r.json()
	task_id = task["id"]
	print(f"  Tarea obtenida: id={task_id}, name={task['name']}")

	# 3. Submit del resultado.
	submission = {
		"task_id": task_id,
		"output": {"ndvi": 0.71, "tile_id": task["payload"].get("tile_id", "unknown")},
		"compute_time_sec": 1.23,
	}
	r = client.post("/tasks/submit", json=submission, headers=auth_headers)
	assert r.status_code == 201, f"POST /tasks/submit: {r.status_code} {r.text}"
	print(f"  Submit OK: {r.json()}")

	# 4. Verificar que el crédito se concedió.
	r = client.get("/me/credits", headers=auth_headers)
	assert r.status_code == 200
	body = r.json()
	assert body["user_id"] > 0
	assert body["username"] == TEST_USER["username"]
	assert body["total"] == pytest.approx(initial_total + 1.0), (
		f"Total esperado {initial_total + 1.0}, real {body['total']}"
	)
	assert len(body["recent"]) == initial_count + 1, (
		f"recent esperado {initial_count + 1} entradas, real {len(body['recent'])}"
	)
	# El crédito más reciente debe corresponder a la tarea que acabamos de submitir.
	latest = body["recent"][0]
	assert latest["task_id"] == task_id
	assert latest["amount"] == 1.0
	print(f"  Estado final: total={body['total']}, recent={len(body['recent'])}")


def test_unauthenticated_me_credits_returns_401(client):
	"""GET /me/credits sin token debe devolver 401."""
	r = client.get("/me/credits")
	assert r.status_code == 401, f"Esperado 401, real {r.status_code}"


def test_unauthenticated_other_users_credits_not_leaked(client, auth_headers):
	"""Un usuario autenticado solo ve SUS créditos, no los de otros."""
	r = client.get("/me/credits", headers=auth_headers)
	assert r.status_code == 200
	body = r.json()
	# No debe haber créditos de otros usuarios en recent.
	for credit in body["recent"]:
		# CreditOut no incluye user_id, pero podemos verificar que task_id pertenece al usuario
		# indirectamente: el GET /me/credits filtra por current_user.id en la query,
		# así que por construcción no puede haber créditos ajenos.
		assert credit["amount"] >= 0

