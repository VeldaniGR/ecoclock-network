"""Fixtures compartidas para los tests del CLI cliente.

Mueve el control de los tests de integración aquí: si no está la variable
ECOCLOCK_RUN_INTEGRATION, los marca como skipped desde el hook de colección
de pytest (más robusto que el `if` por-test, y se ejecuta antes de los tests).
"""
from __future__ import annotations

import os
import pytest


# --- Hook: skip de integration tests por defecto ----------------------------

def pytest_collection_modifyitems(config, items):
    if os.environ.get("ECOCLOCK_RUN_INTEGRATION"):
        return  # el usuario quiere correrlos
    skip_integ = pytest.mark.skip(reason="integration off (set ECOCLOCK_RUN_INTEGRATION=1)")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integ)


# --- Fixtures ---------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolate_token_store(tmp_path, monkeypatch):
    """Cada test usa un XDG_CONFIG_HOME temporal."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))


@pytest.fixture
def base_url():
    return os.environ.get("ECOCLOCK_BASE_URL", "http://127.0.0.1:8000")
