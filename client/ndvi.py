"""Stub de cómputo por tipo de tarea (NDVI / posidonia)."""
from __future__ import annotations

import random
import time
from typing import Any


def compute(task: dict[str, Any]) -> dict[str, Any]:
    """Cálculo stub según payload.type. Más adelante: worker real."""
    payload = task.get("payload") or {}
    if isinstance(payload, str):
        import json
        payload = json.loads(payload)

    task_type = payload.get("type") or "ndvi"
    started = time.time()

    # Simula un poco de trabajo (auto mode verá compute_time_sec > 0)
    time.sleep(random.uniform(0.05, 0.25))

    if task_type == "posidonia":
        unit_id = payload.get("unit_id") or "unknown"
        value = round(random.uniform(500.0, 25000.0), 1)
        return {
            "type": "posidonia",
            "version": 1,
            "unit_id": unit_id,
            "metric": "surface_m2",
            "value": value,
            "unit": "m2",
            "method": "placeholder",
            "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    # Default: NDVI
    return {"ndvi": round(random.uniform(0.1, 0.9), 4), "type": "ndvi"}
