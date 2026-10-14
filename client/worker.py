"""Worker de tareas Eco'clock (cliente).

Beta: stubs con method=placeholder.
Producción: sustituir _compute_ndvi / _compute_posidonia por algoritmos reales
sin cambiar el contrato de salida ni CLI/GUI.
"""
from __future__ import annotations

import json
import random
import time
from typing import Any


def _payload(task: dict[str, Any]) -> dict[str, Any]:
    raw = task.get("payload") or {}
    if isinstance(raw, str):
        raw = json.loads(raw)
    return raw if isinstance(raw, dict) else {}


def _compute_ndvi(payload: dict[str, Any]) -> dict[str, Any]:
    bands = payload.get("bands") or {}
    red = bands.get("red")
    nir = bands.get("nir")
    if isinstance(red, (int, float)) and isinstance(nir, (int, float)):
        denom = (nir + red) or 1e-9
        ndvi = (nir - red) / denom
        ndvi = max(-1.0, min(1.0, float(ndvi)))
        method = "formula_bands"
    else:
        time.sleep(random.uniform(0.05, 0.2))
        ndvi = round(random.uniform(0.1, 0.9), 4)
        method = "placeholder"
    return {
        "type": "ndvi",
        "version": 1,
        "ndvi": round(ndvi, 4),
        "method": method,
        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def _compute_posidonia(payload: dict[str, Any]) -> dict[str, Any]:
    unit_id = payload.get("unit_id") or "unknown"
    # Beta: simulación. Más adelante: clasificación Sentinel-2 sobre bbox.
    time.sleep(random.uniform(0.08, 0.3))
    value = round(random.uniform(500.0, 25000.0), 1)
    return {
        "type": "posidonia",
        "version": 1,
        "unit_id": unit_id,
        "metric": "surface_m2",
        "value": value,
        "unit": "m2",
        "method": "placeholder",
        "source": (payload.get("source") or {}).get("name"),
        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }



def _compute_biodiversity(payload: dict[str, Any]) -> dict[str, Any]:
    """Stub beta: riqueza de especies. Producción: consulta GBIF real o worker offline."""
    unit_id = payload.get("unit_id") or "unknown"
    params = payload.get("params") or {}
    metric = params.get("metric") or "species_richness"
    time.sleep(random.uniform(0.1, 0.35))
    # Placeholder: entero plausible de riqueza en una celda
    value = int(random.uniform(15, 420))
    return {
        "type": "biodiversity",
        "version": 1,
        "unit_id": unit_id,
        "metric": metric,
        "value": value,
        "unit": "species_count",
        "method": "placeholder",
        "source": (payload.get("source") or {}).get("name"),
        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

def compute(task: dict[str, Any]) -> dict[str, Any]:
    """Punto único CLI / GUI / auto. Salida siempre dict JSON-serializable."""
    payload = _payload(task)
    task_type = (payload.get("type") or "ndvi").lower()
    if task_type == "posidonia":
        return _compute_posidonia(payload)
    if task_type == "biodiversity":
        return _compute_biodiversity(payload)
    return _compute_ndvi(payload)
