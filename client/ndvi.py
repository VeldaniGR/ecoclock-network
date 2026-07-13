"""Stub de cálculo NDVI (Fase 0/1).

En Fase 3, esta función se reemplaza por el cálculo real sobre datos
reales (landsat, sentinel, etc.) sin tocar cli.py.
"""
from __future__ import annotations

import random
import time
from typing import Any


def compute(task: dict[str, Any]) -> dict[str, Any]:
    """Devuelve un NDVI dummy entre 0.1 y 0.9. Simula un poco de cómputo."""
    time.sleep(random.uniform(0.05, 0.2))
    return {"ndvi": round(random.uniform(0.1, 0.9), 4)}
