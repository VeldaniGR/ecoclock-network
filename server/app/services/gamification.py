"""Cálculo de niveles y logros (Fase B)."""
from __future__ import annotations

from datetime import datetime
from typing import Any


LEVELS = [
    {"id": 1, "name": "Explorador", "min_tasks": 1, "min_active_days": 0, "min_streak": 0, "min_types": 0},
    {"id": 2, "name": "Sensor", "min_tasks": 25, "min_active_days": 3, "min_streak": 0, "min_types": 0},
    {"id": 3, "name": "Centinela", "min_tasks": 100, "min_active_days": 10, "min_streak": 7, "min_types": 2},
    {"id": 4, "name": "Faro", "min_tasks": 500, "min_active_days": 20, "min_streak": 14, "min_types": 3},
]

ACHIEVEMENT_DEFS = [
    {"id": "first_task", "name": "Primera contribución"},
    {"id": "streak_7", "name": "Semana en activo"},
    {"id": "two_habitats", "name": "Dos hábitats"},
]


def _meets(level: dict, tasks: int, active_days: int, streak: int, n_types: int) -> bool:
    return (
        tasks >= level["min_tasks"]
        and active_days >= level["min_active_days"]
        and streak >= level["min_streak"]
        and n_types >= level["min_types"]
    )


def compute_level(
    tasks_done: int,
    active_days: int,
    streak_days: int,
    task_types: list[str],
) -> dict[str, Any]:
    n_types = len(set(t.lower() for t in task_types if t))
    current = None
    for lv in LEVELS:
        if _meets(lv, tasks_done, active_days, streak_days, n_types):
            current = lv
        else:
            break

    if current is None:
        # Sin ninguna tarea
        nxt = LEVELS[0]
        return {
            "id": 0,
            "name": "Recién llegado",
            "next_id": nxt["id"],
            "next_name": nxt["name"],
            "progress": 0.0,
        }

    idx = next(i for i, lv in enumerate(LEVELS) if lv["id"] == current["id"])
    if idx >= len(LEVELS) - 1:
        return {
            "id": current["id"],
            "name": current["name"],
            "next_id": None,
            "next_name": None,
            "progress": 1.0,
        }

    nxt = LEVELS[idx + 1]
    # Progreso simple por tareas hacia el siguiente umbral
    span = max(1, nxt["min_tasks"] - current["min_tasks"])
    done = max(0, tasks_done - current["min_tasks"])
    progress = min(1.0, done / span)

    return {
        "id": current["id"],
        "name": current["name"],
        "next_id": nxt["id"],
        "next_name": nxt["name"],
        "progress": round(progress, 3),
    }


def compute_achievements(
    tasks_done: int,
    streak_days: int,
    task_types: list[str],
    last_active_at: datetime | None,
) -> list[dict[str, Any]]:
    types_lower = {t.lower() for t in task_types if t}
    has_two_habitats = (
        ("ndvi" in types_lower and "posidonia" in types_lower)
        or len(types_lower) >= 2
    )

    unlocked = {
        "first_task": tasks_done >= 1,
        "streak_7": streak_days >= 7,
        "two_habitats": has_two_habitats,
    }

    # Fecha aproximada: usamos last_active_at si está desbloqueado (suficiente para v1)
    out = []
    for defn in ACHIEVEMENT_DEFS:
        aid = defn["id"]
        out.append({
            "id": aid,
            "name": defn["name"],
            "unlocked_at": last_active_at if unlocked.get(aid) else None,
        })
    return out
