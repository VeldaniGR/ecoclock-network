"""Validación de resultados enviados por el cliente (capa 1).

Rechaza outputs mal formados o fuera de rangos plausibles.
No sustituye el consenso entre peers (capa 2).
"""
from __future__ import annotations

import json
from typing import Any


class OutputValidationError(ValueError):
    """Output inválido respecto al contrato de la tarea."""


def _as_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as e:
            raise OutputValidationError(f"payload no es JSON: {e}") from e
    if not isinstance(raw, dict):
        raise OutputValidationError("se esperaba un objeto JSON")
    return raw


def _require(out: dict[str, Any], *keys: str) -> None:
    missing = [k for k in keys if k not in out]
    if missing:
        raise OutputValidationError(f"faltan campos: {', '.join(missing)}")


def validate_output(task_payload: Any, output: Any) -> dict[str, Any]:
    """Valida output contra el tipo de la tarea. Devuelve output normalizado (dict)."""
    payload = _as_dict(task_payload) if task_payload is not None else {}
    out = _as_dict(output)
    task_type = (payload.get("type") or out.get("type") or "ndvi").lower()

    if task_type == "ndvi":
        return _validate_ndvi(out)
    if task_type == "posidonia":
        return _validate_posidonia(out, payload)
    if task_type == "biodiversity":
        return _validate_biodiversity(out, payload)
    # Tipos desconocidos: exigir al menos type + version
    _require(out, "type")
    return out


def _validate_ndvi(out: dict[str, Any]) -> dict[str, Any]:
    _require(out, "type", "ndvi")
    if out.get("type") != "ndvi":
        raise OutputValidationError("type debe ser 'ndvi'")
    v = out.get("ndvi")
    if not isinstance(v, (int, float)):
        raise OutputValidationError("ndvi debe ser numérico")
    if not -1.0 <= float(v) <= 1.0:
        raise OutputValidationError("ndvi fuera de rango [-1, 1]")
    return out


def _validate_posidonia(out: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    _require(out, "type", "value", "metric")
    if out.get("type") != "posidonia":
        raise OutputValidationError("type debe ser 'posidonia'")
    v = out.get("value")
    if not isinstance(v, (int, float)):
        raise OutputValidationError("value debe ser numérico")
    if float(v) < 0:
        raise OutputValidationError("superficie no puede ser negativa")
    # Tope anti-basura (m²); ajustar cuando haya tiles reales
    if float(v) > 1e9:
        raise OutputValidationError("value irrealmente alto")
    if out.get("metric") not in (None, "surface_m2", payload.get("params", {}).get("metric")):
        # metric surface_m2 esperado en v1
        if out.get("metric") != "surface_m2":
            raise OutputValidationError("metric debe ser surface_m2")
    return out


def _validate_biodiversity(out: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    _require(out, "type", "value", "metric")
    if out.get("type") != "biodiversity":
        raise OutputValidationError("type debe ser 'biodiversity'")
    v = out.get("value")
    if not isinstance(v, (int, float)):
        raise OutputValidationError("value debe ser numérico")
    if float(v) < 0:
        raise OutputValidationError("riqueza no puede ser negativa")
    if float(v) > 100_000:
        raise OutputValidationError("value irrealmente alto para species_richness")
    expected = (payload.get("params") or {}).get("metric") or "species_richness"
    if out.get("metric") != expected and out.get("metric") != "species_richness":
        raise OutputValidationError(f"metric debe ser {expected}")
    return out
