"""Tests end-to-end del MVP de Ecoclock Network. Asume que el servidor está corriendo en http://127.0.0.1:8000. Los tests usan uuid en usernames para evitar conflictos entre runs."""
import uuid

import httpx

BASE_URL = "http://127.0.0.1:8000"

TIMEOUT = 10.0

def _unique_user() -> dict:
	"""Genera credenciales únicas para cada test."""
	suffix = uuid.uuid4().hex[:8]
	return {
		"email": f"test-{suffix}@example.com",
		"username": f"tester-{suffix}",
		"password": f"pass-{uuid.uuid4().hex}",
	}

def test_health():
	"""/health responde sin auth."""
	r = httpx.get(f"{BASE_URL}/health", timeout=TIMEOUT)
	assert r.status_code == 200
	body = r.json()
	assert body["status"] == "ok"
	assert body["service"] == "ecoclock-network"

def test_register_creates_user():
	"""Register devuelve 201 y datos del user creado."""
	user = _unique_user()
	r = httpx.post(
		f"{BASE_URL}/auth/register",
		json={"email": user["email"], "username": user["username"], "password": user["password"]},
		timeout=TIMEOUT,
	)
	assert r.status_code == 201, f"register falló: {r.status_code} {r.text}"
	body = r.json()
	assert body["email"] == user["email"]
	assert body["username"] == user["username"]
	assert "id" in body

def test_register_duplicate_email_returns_400():
	"""Registrar el mismo email dos veces devuelve 400."""
	user = _unique_user()
	httpx.post(
		f"{BASE_URL}/auth/register",
		json={"email": user["email"], "username": user["username"], "password": user["password"]},
		timeout=TIMEOUT,
	)
	r = httpx.post(
		f"{BASE_URL}/auth/register",
		json={"email": user["email"], "username": "otro", "password": user["password"]},
		timeout=TIMEOUT,
	)
	assert r.status_code == 400

def test_login_returns_token():
	"""Login con credenciales válidas devuelve access_token."""
	user = _unique_user()
	httpx.post(
		f"{BASE_URL}/auth/register",
		json={"email": user["email"], "username": user["username"], "password": user["password"]},
		timeout=TIMEOUT,
	)
	r = httpx.post(
		f"{BASE_URL}/auth/login",
		json={"username": user["username"], "password": user["password"]},
		timeout=TIMEOUT,
	)
	assert r.status_code == 200, f"login falló: {r.status_code} {r.text}"
	body = r.json()
	assert "access_token" in body
	assert body["token_type"] == "bearer"
	assert len(body["access_token"]) > 20

def test_me_with_valid_token():
	"""/auth/me con Bearer token devuelve datos del usuario."""
	user = _unique_user()
	httpx.post(
		f"{BASE_URL}/auth/register",
		json={"email": user["email"], "username": user["username"], "password": user["password"]},
		timeout=TIMEOUT,
	)
	login = httpx.post(
		f"{BASE_URL}/auth/login",
		json={"username": user["username"], "password": user["password"]},
		timeout=TIMEOUT,
	).json()
	token = login["access_token"]
	r = httpx.get(
	f"{BASE_URL}/auth/me",
	headers={"Authorization": f"Bearer {token}"},
	timeout=TIMEOUT,
	)
	assert r.status_code == 200, f"/auth/me falló: {r.status_code} {r.text}"
	body = r.json()
	assert body["username"] == user["username"]
	assert body["email"] == user["email"]

def test_me_without_token_returns_401():
	"""/auth/me sin token devuelve 401."""
	r = httpx.get(f"{BASE_URL}/auth/me", timeout=TIMEOUT)
	assert r.status_code == 401

def test_next_task_creates_and_returns():
	"""/tasks/next devuelve una tarea (crea dummy si no hay pendientes)."""
	user = _unique_user()
	httpx.post(
		f"{BASE_URL}/auth/register",
		json={"email": user["email"], "username": user["username"], "password": user["password"]},
  		timeout=TIMEOUT,
	)
	token = httpx.post(
 		f"{BASE_URL}/auth/login",
 		json={"username": user["username"], "password": user["password"]},
 		timeout=TIMEOUT,
	).json()["access_token"]
	r = httpx.get(
 		f"{BASE_URL}/tasks/next",
 		headers={"Authorization": f"Bearer {token}"},
 		timeout=TIMEOUT,
	)
	assert r.status_code == 200, f"/tasks/next falló: {r.status_code} {r.text}"
	body = r.json()
	assert "id" in body
	assert "name" in body
	assert body["status"] in ("assigned", "pending")


def test_submit_task_result():
	"""/tasks/submit guarda un resultado y marca la tarea como done."""
	user = _unique_user()
	httpx.post(
		f"{BASE_URL}/auth/register",
		json={"email": user["email"], "username": user["username"], "password": user["password"]},
		timeout=TIMEOUT,
	)
	token = httpx.post(
		f"{BASE_URL}/auth/login",
		json={"username": user["username"], "password": user["password"]},
		timeout=TIMEOUT,
 	).json()["access_token"]
	task = httpx.get(
		f"{BASE_URL}/tasks/next",
		headers={"Authorization": f"Bearer {token}"},
 		timeout=TIMEOUT,
	).json()
	r = httpx.post(
		f"{BASE_URL}/tasks/submit",
		json={"task_id": task["id"], "output": {"ndvi": 0.65}, "compute_time_sec": 1.23},
		headers={"Authorization": f"Bearer {token}"},
		timeout=TIMEOUT,
	)
	assert r.status_code == 201, f"/tasks/submit falló: {r.status_code} {r.text}"
	body = r.json()
	assert body["task_id"] == task["id"]
	assert body["output"] == {"ndvi": 0.65}


def test_submit_without_auth_returns_401():
	"""/tasks/submit sin token devuelve 401."""
	r = httpx.post(
		f"{BASE_URL}/tasks/submit",
		json={"task_id": 1, "output": {"x": 1}},
		timeout=TIMEOUT,
	)
	assert r.status_code == 401

