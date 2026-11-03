#!/usr/bin/env python3
"""
Reposición de cola de tareas árticas (mapa de impacto).

Si hay menos de --min-arctic tareas pending con region=arctic (o name arctic-*),
crea hasta --fill-to.

Uso:
  PYTHONPATH=/app python /app/scripts/replenish_arctic_queue.py
  PYTHONPATH=/app python /app/scripts/replenish_arctic_queue.py --min-arctic 4 --fill-to 12
  PYTHONPATH=/app python /app/scripts/replenish_arctic_queue.py --dry-run

Cron (cada hora, ejemplo en el host):
  0 * * * * cd /opt/ecoclock-network && docker compose exec -T -e PYTHONPATH=/app api \
    python /app/scripts/replenish_arctic_queue.py --min-arctic 4 --fill-to 10 \
    >> /var/log/ecoclock-arctic-replenish.log 2>&1
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

from sqlalchemy import func, or_, select

from app.db.database import AsyncSessionLocal
from app.db.models import Task

ARCTIC_AOIS = [
    {"id": "svalbard-adventfjorden", "label": "Svalbard · Adventfjorden",
     "min_lon": 15.3, "min_lat": 78.15, "max_lon": 15.9, "max_lat": 78.35},
    {"id": "svalbard-nyalesund", "label": "Svalbard · Ny-Alesund",
     "min_lon": 11.7, "min_lat": 78.85, "max_lon": 12.2, "max_lat": 79.05},
    {"id": "greenland-ilulissat", "label": "Groenlandia · Ilulissat",
     "min_lon": -51.5, "min_lat": 69.0, "max_lon": -50.5, "max_lat": 69.5},
    {"id": "greenland-scoresby", "label": "Groenlandia · Scoresby Sund",
     "min_lon": -28.0, "min_lat": 70.0, "max_lon": -22.0, "max_lat": 71.5},
    {"id": "barents-bjornoya", "label": "Mar de Barents · Bjornoya",
     "min_lon": 18.5, "min_lat": 74.3, "max_lon": 19.5, "max_lat": 74.6},
    {"id": "canada-resolute", "label": "Artico canadiense · Resolute",
     "min_lon": -95.5, "min_lat": 74.5, "max_lon": -94.5, "max_lat": 74.9},
    {"id": "alaska-barrow", "label": "Alaska · Utqiagvik",
     "min_lon": -157.0, "min_lat": 71.2, "max_lon": -156.2, "max_lat": 71.5},
    {"id": "russia-severnaya", "label": "Rusia · Severnaya Zemlya",
     "min_lon": 95.0, "min_lat": 78.0, "max_lon": 100.0, "max_lat": 80.0},
]


def make_payload(aoi: dict, idx: int) -> dict:
    return {
        "type": "ndvi",
        "version": 1,
        "tile_id": f"ARCTIC_{aoi['id'].upper()}_{idx}",
        "datetime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bbox": {
            "min_lon": aoi["min_lon"], "min_lat": aoi["min_lat"],
            "max_lon": aoi["max_lon"], "max_lat": aoi["max_lat"],
            "crs": "EPSG:4326",
        },
        "aoi_label": aoi["label"],
        "region": "arctic",
        "bands": {"red": 0.04 + (idx % 5) * 0.01, "nir": 0.18 + (idx % 5) * 0.02},
        "description": f"NDVI Artico — {aoi['label']} (mapa de impacto)",
        "params": {"theme": "arctic_ice_melt"},
    }


async def count_pending_arctic(db) -> int:
    # pending cuyo name empiece por arctic- o payload contenga region arctic
    result = await db.execute(
        select(func.count()).select_from(Task).where(
            Task.status == "pending",
            or_(
                Task.name.like("arctic-%"),
                Task.name.like("arctic-auto-%"),
            ),
        )
    )
    return int(result.scalar_one() or 0)


async def replenish(*, min_arctic: int, fill_to: int, dry_run: bool) -> None:
    if fill_to < min_arctic:
        fill_to = min_arctic

    async with AsyncSessionLocal() as db:
        pending = await count_pending_arctic(db)
        print(f"Pending árticas: {pending} (umbral={min_arctic}, objetivo={fill_to})")
        if pending >= min_arctic:
            print("Cola ártica suficiente. No se crea nada.")
            return

        need = fill_to - pending
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        print(f"Creando {need} tarea(s) ártica(s)...")

        for i in range(need):
            aoi = ARCTIC_AOIS[i % len(ARCTIC_AOIS)]
            name = f"arctic-ndvi-{aoi['id']}-{i}-{int(now.timestamp())}"
            payload = make_payload(aoi, i)
            if dry_run:
                print(f"  [dry-run] {name} · {aoi['label']}")
                continue
            db.add(Task(
                name=name,
                payload=json.dumps(payload),
                status="pending",
                created_at=now,
            ))

        if not dry_run:
            await db.commit()
        print("OK replenish ártico")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--min-arctic", type=int, default=4)
    p.add_argument("--fill-to", type=int, default=10)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    asyncio.run(replenish(
        min_arctic=args.min_arctic,
        fill_to=args.fill_to,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()
