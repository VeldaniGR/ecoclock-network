"""Cliente mínimo CDSE: token OAuth para catálogo / descargas."""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import settings

_token: str | None = None
_token_expires_at: float = 0.0


class CopernicusConfigError(RuntimeError):
    """Faltan credenciales CDSE en .env."""


class CopernicusAuthError(RuntimeError):
    """No se pudo obtener el access_token."""


def _credentials_configured() -> bool:
    return bool(settings.CDSE_USERNAME and settings.CDSE_PASSWORD)


def get_cdse_token(*, force_refresh: bool = False) -> str:
    """Devuelve un access_token de CDSE (con caché en memoria)."""
    global _token, _token_expires_at

    if not _credentials_configured():
        raise CopernicusConfigError(
            "CDSE_USERNAME / CDSE_PASSWORD no configurados en .env"
        )

    now = time.time()
    if not force_refresh and _token and now < (_token_expires_at - 60):
        return _token

    data = {
        "client_id": settings.CDSE_CLIENT_ID,
        "username": settings.CDSE_USERNAME,
        "password": settings.CDSE_PASSWORD,
        "grant_type": "password",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                settings.CDSE_TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.HTTPError as exc:
        raise CopernicusAuthError(f"Error de red al pedir token CDSE: {exc}") from exc

    if response.status_code != 200:
        raise CopernicusAuthError(
            f"CDSE auth falló HTTP {response.status_code}: {response.text[:300]}"
        )

    payload: dict[str, Any] = response.json()
    access = payload.get("access_token")
    if not access:
        raise CopernicusAuthError("Respuesta CDSE sin access_token")

    expires_in = int(payload.get("expires_in") or 600)
    _token = access
    _token_expires_at = now + expires_in
    return access


def cdse_auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {get_cdse_token()}"}
