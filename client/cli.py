#!/usr/bin/env python3
"""Eco'clock Network — CLI cliente (Fase 1).
Sub-comandos:
  register   Crea un usuario nuevo.
  login      Inicia sesión y guarda el token.
  me         Muestra los datos del usuario autenticado.
  next       Pide la siguiente tarea al servidor.
  submit     Envía el resultado de una tarea.
  run        Flujo completo: auth -> next -> compute (stub) -> submit.
  logout     Borra el token guardado.

El procesamiento NDVI es un stub (Fase 0/1). En Fase 3, `client.ndvi.compute`
se reemplaza por el cálculo real sin tocar el flujo del CLI.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable

import requests
# --- Sub-comando opcional: gui (PyQt6) -------------------------------------
try:
	from .gui import app as _gui_app
except ImportError:  # PyQt6 no instalado: el sub-comando gui fallara bonito
	_gui_app = None

# --- Constants ---------------------------------------------------------------

DEFAULT_BASE_URL = "https://api.ecoclock.org"
TIMEOUT = float(os.environ.get("ECOCLOCK_TIMEOUT", "10"))

# --- Version ---
__cli_version__ = "0.5.0"  # Sincronizada con el tag. release.yml la sobreescribe en build.


def _token_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return base / "ecoclock" / "token.json"


# --- Errors ------------------------------------------------------------------

class CLIError(RuntimeError):
    """Error de uso o de respuesta del servidor."""


# --- Token store -------------------------------------------------------------

def save_token(token: str) -> None:
    p = _token_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"access_token": token}, indent=2))
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def load_token() -> str | None:
    p = _token_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return data.get("access_token")


def clear_token() -> None:
    p = _token_path()
    if p.exists():
        p.unlink()


# --- HTTP helpers ------------------------------------------------------------

def _url(base: str, path: str) -> str:
    return base.rstrip("/") + path


def _raise_for_status(r: requests.Response) -> None:
    if r.status_code >= 400:
        try:
            detail = r.json()
        except ValueError:
            detail = r.text
        raise CLIError(f"HTTP {r.status_code}: {detail}")


def auth_headers(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


# --- Sub-commands ------------------------------------------------------------

def cmd_register(args: argparse.Namespace) -> dict[str, Any]:
    payload = {"email": args.email, "username": args.username, "password": args.password}
    r = requests.post(_url(args.base_url, "/auth/register"), json=payload, timeout=TIMEOUT)
    _raise_for_status(r)
    return r.json()


def cmd_login(args: argparse.Namespace) -> dict[str, Any]:
    payload = {"username": args.username, "password": args.password}
    r = requests.post(_url(args.base_url, "/auth/login"), json=payload, timeout=TIMEOUT)
    _raise_for_status(r)
    body = r.json()
    if "access_token" not in body:
        raise CLIError("Login OK pero el cuerpo no trae 'access_token'.")
    save_token(body["access_token"])
    return body


def cmd_me(args: argparse.Namespace) -> dict[str, Any]:
    token = args.token or load_token()
    if not token:
        raise CLIError("No hay token. Ejecuta `login` o `register` primero.")
    r = requests.get(_url(args.base_url, "/auth/me"), headers=auth_headers(token), timeout=TIMEOUT)
    _raise_for_status(r)
    return r.json()


def cmd_next(args: argparse.Namespace) -> dict[str, Any]:
    token = args.token or load_token()
    if not token:
        raise CLIError("No hay token. Ejecuta `login` o `register` primero.")
    r = requests.get(_url(args.base_url, "/tasks/next"), headers=auth_headers(token), timeout=TIMEOUT)
    _raise_for_status(r)
    return r.json()


def cmd_submit(args: argparse.Namespace) -> dict[str, Any]:
    token = args.token or load_token()
    if not token:
        raise CLIError("No hay token. Ejecuta `login` o `register` primero.")
    payload = {
        "task_id": args.task_id,
        "output": json.loads(args.output),
        "compute_time_sec": args.compute_time_sec,
    }
    r = requests.post(_url(args.base_url, "/tasks/submit"), json=payload,
                      headers=auth_headers(token), timeout=TIMEOUT)
    _raise_for_status(r)
    return r.json()


# --- Helper para run() -------------------------------------------------------

def _call(func: Callable[..., dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    """Llama a un sub-comando con kwargs en lugar de un Namespace."""
    return func(argparse.Namespace(**kwargs))


def _auth(args: argparse.Namespace) -> str:
    """Asegura token. Prioridad: --token *** guardado > register/login."""
    if args.token:
        return args.token

    token = load_token()
    if token and not args.force_register:
        return token

    creds = {
        "base_url": args.base_url,
        "email": args.email,
        "username": args.username,
        "password": args.password,
    }

    if args.register or not args.login:
        try:
            _call(cmd_register, **creds)
        except CLIError as e:
            if not (args.login and "HTTP 400" in str(e)):
                raise
            return _call(cmd_login, **creds)["access_token"]
    return _call(cmd_login, **creds)["access_token"]


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    """Flujo completo: auth -> next -> compute (stub) -> submit."""
    from . import ndvi

    token = _auth(args)
    args.token = token

    task = cmd_next(args)
    print(f"[+] Tarea recibida: id={task.get('id')} name={task.get('name')} status={task.get('status')}")

    started = time.time()
    output = ndvi.compute(task)
    compute_time = time.time() - started

    args.task_id = task["id"]
    args.output = json.dumps(output)
    args.compute_time_sec = round(compute_time, 3)
    result = cmd_submit(args)
    print(f"[+] Resultado enviado: task_id={result.get('task_id')} status={result.get('status')}")
    return result


def cmd_gui(args: argparse.Namespace) -> dict[str, Any]:
	"""Lanza la GUI PyQt6 (Fase 2). PyQt6 debe estar instalado."""
	if _gui_app is None:
		raise CLIError(
	"PyQt6 no esta instalado. Instala con: pip install -r client/requirements-gui.txt"
		)
	rc = _gui_app.main()
	return {"ok": True, "returncode": rc}

def cmd_update(args: argparse.Namespace) -> dict[str, Any]:
    """Auto-actualiza el binario desde GitHub releases.

    --check -> solo informa, no descarga ni reemplaza nada.
    """
    import tempfile

    current = __cli_version__
    plat_norm = "windows-x86_64.exe" if sys.platform.startswith("win") else "linux-x86_64"
    repo = "veldanigr/ecoclock-network"
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"

    # 1) Consultar latest release
    try:
        r = requests.get(api_url, timeout=TIMEOUT, headers={"Accept": "application/vnd.github+json"})
    except requests.RequestException as e:
        raise CLIError(f"Sin red al consultar GitHub: {e}")
    _raise_for_status(r)
    release = r.json()
    latest_tag = release.get("tag_name") or ""
    latest_ver = latest_tag.lstrip("v")

    if latest_ver == current:
        print(f"[i] Ya estas en la ultima version ({current}).")
        return {"ok": True, "action": "noop", "current": current, "latest": latest_ver}

    # 2) Encontrar asset para nuestra plataforma
    asset_name = f"ecoclock-cli-{latest_tag}-{plat_norm}"
    asset = next((a for a in release.get("assets", []) if a.get("name") == asset_name), None)
    if asset is None:
        raise CLIError(
            f"El release {latest_tag} no incluye el asset '{asset_name}'. "
            f"Assets disponibles: {[a.get('name') for a in release.get('assets', [])]}"
        )
    download_url = asset["browser_download_url"]
    asset_size = asset.get("size", 0)

    # 3) --check: informar y salir
    if getattr(args, "check", False):
        print(f"[check] actual={current}  latest={latest_ver}  url={download_url}")
        return {"ok": True, "action": "check", "current": current, "latest": latest_ver, "url": download_url}

    # 4) Descargar a tempfile junto al binario (mismo dir = os.replace atomico)
    bin_path = Path(sys.argv[0]).resolve()
    bin_dir = bin_path.parent
    tmp_fd, tmp_path = tempfile.mkstemp(prefix=".ecoclock-update-", suffix=".tmp", dir=bin_dir)
    os.close(tmp_fd)
    tmp = Path(tmp_path)

    try:
        print(f"[+] Descargando {asset_name} ({asset_size} bytes)...")
        with requests.get(download_url, timeout=TIMEOUT, stream=True) as dr:
            _raise_for_status(dr)
            with open(tmp, "wb") as f:
                for chunk in dr.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)

        # Validacion minima: tamano no nulo
        if tmp.stat().st_size == 0:
            raise CLIError("Descarga vacia. Binario original intacto.")

        # Permisos de ejecucion
        tmp.chmod(0o755)

        # Replace atomico + re-exec
        os.replace(tmp, bin_path)
        print(f"[+] Binario actualizado a {latest_ver}. Relanzando...")
        os.execv(str(bin_path), sys.argv)
    except BaseException:
        # Si algo falla, limpiar tempfile y relanzar excepcion
        try:
            tmp.unlink()
        except OSError:
            pass
        raise

    # Inalcanzable: os.execv no retorna si todo va bien
    return {"ok": True, "action": "updated", "current": current, "latest": latest_ver}


def cmd_logout(args: argparse.Namespace) -> dict[str, Any]:
    clear_token()
    return {"ok": True, "path": str(_token_path())}


# --- Argparse ----------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ecoclock", description="Eco'clock Network CLI (Fase 1)")
    p.add_argument("--base-url", default=None,
                   help=f"URL del servidor (default: {DEFAULT_BASE_URL})")

    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("register", help="Crear un usuario nuevo")
    s.add_argument("--email", required=True)
    s.add_argument("--username", required=True)
    s.add_argument("--password", required=True)
    s.set_defaults(func=cmd_register)

    s = sub.add_parser("login", help="Iniciar sesión y guardar el token")
    s.add_argument("--username", required=True)
    s.add_argument("--password", required=True)
    s.set_defaults(func=cmd_login)

    s = sub.add_parser("me", help="Datos del usuario autenticado")
    s.add_argument("--token", help="Token (si no, usa el guardado)")
    s.set_defaults(func=cmd_me)

    s = sub.add_parser("next", help="Pedir la siguiente tarea")
    s.add_argument("--token", help="Token (si no, usa el guardado)")
    s.set_defaults(func=cmd_next)

    s = sub.add_parser("submit", help="Enviar el resultado de una tarea")
    s.add_argument("--task-id", type=int, required=True)
    s.add_argument("--output", required=True, help="JSON string, p.ej. '{\"ndvi\": 0.65}'")
    s.add_argument("--compute-time-sec", type=float, default=0.0)
    s.add_argument("--token", help="Token (si no, usa el guardado)")
    s.set_defaults(func=cmd_submit)

    s = sub.add_parser("run", help="Flujo completo: auth + next + compute + submit")
    s.add_argument("--email", default=os.environ.get("ECOCLOCK_EMAIL", ""))
    s.add_argument("--username", default=os.environ.get("ECOCLOCK_USERNAME", ""))
    s.add_argument("--password", default=os.environ.get("ECOCLOCK_PASSWORD", ""))
    s.add_argument("--register", action="store_true", help="Hacer register antes de login")
    s.add_argument("--login", action="store_true", help="Hacer login siempre")
    s.add_argument("--force-register", action="store_true",
                   help="Ignorar token guardado y registrar de nuevo")
    s.add_argument("--token", help="Token (si no, usa el guardado)")
    s.set_defaults(func=cmd_run)
    s = sub.add_parser("gui", help="Lanzar la GUI (Fase 2, requiere PyQt6)")
    s.set_defaults(func=cmd_gui)
    s = sub.add_parser("update", help="Auto-actualizar el binario desde GitHub releases")
    s.add_argument("--check", action="store_true", help="Solo informa, no descarga ni reemplaza")
    s.set_defaults(func=cmd_update)
    s = sub.add_parser("logout", help="Borrar el token guardado")
    s.set_defaults(func=cmd_logout)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.base_url:
        args.base_url = os.environ.get("ECOCLOCK_BASE_URL") or DEFAULT_BASE_URL
    try:
        result = args.func(args)
    except CLIError as e:
        print(f"[!] {e}", file=sys.stderr)
        return 1
    except requests.RequestException as e:
        print(f"[!] Error de red: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
