#!/usr/bin/env python3
"""
Reposición de cola de tareas árticas (mapa de impacto).

Si hay menos de --min-arctic tareas pending con region=arctic (o name arctic-*),
crea hasta --fill-to.

Uso:
  PYTHONPATH=/app python /app/scripts/replenish_arctic_queue.py
  PYTHONPATH=/app python /app/scripts/replenish_arctic_queue.py --min-arctic 8 --fill-to 20
  PYTHONPATH=/app python /app/scripts/replenish_arctic_queue.py --dry-run

Cron (cada hora, ejemplo en el host):
  0 * * * * cd /opt/ecoclock-network && docker compose exec -T -e PYTHONPATH=/app api \
    python /app/scripts/replenish_arctic_queue.py --min-arctic 8 --fill-to 20 \
    >> /var/log/ecoclock-arctic-replenish.log 2>&1
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
from datetime import datetime, timezone

from sqlalchemy import func, or_, select

from app.db.database import AsyncSessionLocal
from app.db.models import Task

# Misma lista que seed_arctic_tasks.py (mantener sincronizada)
ARCTIC_AOIS = [
    # --- originales ---
    {
        "id": "svalbard-adventfjorden",
        "label": "Svalbard · Adventfjorden",
        "min_lon": 15.3, "min_lat": 78.15,
        "max_lon": 15.9, "max_lat": 78.35,
    },
    {
        "id": "svalbard-nyalesund",
        "label": "Svalbard · Ny-Ålesund",
        "min_lon": 11.7, "min_lat": 78.85,
        "max_lon": 12.2, "max_lat": 79.05,
    },
    {
        "id": "greenland-ilulissat",
        "label": "Groenlandia · Ilulissat / Disko Bay",
        "min_lon": -51.5, "min_lat": 69.0,
        "max_lon": -50.5, "max_lat": 69.5,
    },
    {
        "id": "greenland-scoresby",
        "label": "Groenlandia · Scoresby Sund",
        "min_lon": -28.0, "min_lat": 70.0,
        "max_lon": -22.0, "max_lat": 71.5,
    },
    {
        "id": "barents-bjornoya",
        "label": "Mar de Barents · Bjørnøya",
        "min_lon": 18.5, "min_lat": 74.3,
        "max_lon": 19.5, "max_lat": 74.6,
    },
    {
        "id": "canada-resolute",
        "label": "Ártico canadiense · Resolute",
        "min_lon": -95.5, "min_lat": 74.5,
        "max_lon": -94.5, "max_lat": 74.9,
    },
    {
        "id": "alaska-barrow",
        "label": "Alaska · Utqiaġvik (Barrow)",
        "min_lon": -157.0, "min_lat": 71.2,
        "max_lon": -156.2, "max_lat": 71.5,
    },
    {
        "id": "russia-severnaya",
        "label": "Rusia · Severnaya Zemlya",
        "min_lon": 95.0, "min_lat": 78.0,
        "max_lon": 100.0, "max_lat": 80.0,
    },
    # --- nuevas (hexágonos distintos) ---
    {
        "id": "greenland-thule",
        "label": "Groenlandia · Qaanaaq / Thule",
        "min_lon": -69.5, "min_lat": 77.3,
        "max_lon": -68.5, "max_lat": 77.7,
    },
    {
        "id": "canada-alert",
        "label": "Ártico canadiense · Alert (Ellesmere)",
        "min_lon": -62.5, "min_lat": 82.3,
        "max_lon": -61.5, "max_lat": 82.6,
    },
    {
        "id": "svalbard-nordaustlandet",
        "label": "Svalbard · Nordaustlandet",
        "min_lon": 20.0, "min_lat": 79.5,
        "max_lon": 25.0, "max_lat": 80.5,
    },
    {
        "id": "franz-josef",
        "label": "Rusia · Tierra de Francisco José",
        "min_lon": 50.0, "min_lat": 80.0,
        "max_lon": 60.0, "max_lat": 81.5,
    },
    {
        "id": "novaya-zemlya",
        "label": "Rusia · Novaya Zemlya (norte)",
        "min_lon": 55.0, "min_lat": 74.0,
        "max_lon": 60.0, "max_lat": 76.0,
    },
    {
        "id": "laptev-leninskiy",
        "label": "Mar de Láptev · zona costera",
        "min_lon": 125.0, "min_lat": 73.0,
        "max_lon": 130.0, "max_lat": 74.5,
    },
    {
        "id": "chukchi-wrangel",
        "label": "Mar de Chukchi · Wrangel",
        "min_lon": -179.5, "min_lat": 70.5,
        "max_lon": -175.0, "max_lat": 72.0,
    },
    {
        "id": "beaufort-banks",
        "label": "Mar de Beaufort · Banks Island",
        "min_lon": -125.0, "min_lat": 72.0,
        "max_lon": -120.0, "max_lat": 74.0,
    },
    {
        "id": "kara-yamal",
        "label": "Mar de Kara · Península de Yamal",
        "min_lon": 68.0, "min_lat": 70.0,
        "max_lon": 72.0, "max_lat": 72.0,
    },
    {
        "id": "greenland-northeast",
        "label": "Groenlandia · Costa NE (Zackenberg)",
        "min_lon": -22.0, "min_lat": 74.0,
        "max_lon": -18.0, "max_lat": 75.0,
    },
    {
        "id": "iceland-north",
        "label": "Islandia norte (margen Ártico)",
        "min_lon": -19.0, "min_lat": 65.5,
        "max_lon": -15.0, "max_lat": 66.5,
    },
    {
        "id": "norway-tromso",
        "label": "Noruega · Tromsø / zona boreal",
        "min_lon": 18.5, "min_lat": 69.5,
        "max_lon": 20.0, "max_lat": 70.0,
    },
]


def make_payload(aoi: dict, idx: int) -> dict:
    # pequeño offset determinista para no coincidir siempre en el mismo centroide
    dj = (idx % 7 - 3) * 0.02
    min_lon = aoi["min_lon"] + dj
    max_lon = aoi["max_lon"] + dj
    min_lat = max(60.0, aoi["min_lat"] + dj)
    max_lat = min(90.0, aoi["max_lat"] + dj)

    return {
        "type": "ndvi",
        "version": 1,
        "tile_id": f"ARCTIC_{aoi['id'].upper()}_{idx}",
        "datetime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bbox": {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat,
            "crs": "EPSG:4326",
        },
        "aoi_label": aoi["label"],
        "region": "arctic",
        "bands": {
            "red": 0.04 + (idx % 5) * 0.01,
            "nir": 0.18 + (idx % 5) * 0.02,
        },
        "description": f"NDVI Ártico — {aoi['label']} (mapa de impacto)",
        "params": {"theme": "arctic_ice_melt"},
    }


async def count_pending_arctic(db) -> int:
    """Pending cuyo name empiece por arctic- o payload contenga region arctic."""
    result = await db.execute(
        select(func.count()).select_from(Task).where(
            Task.status == "pending",
            or_(
                Task.name.like("arctic-%"),
                Task.name.like("arctic-auto-%"),
                Task.payload.like('%"region": "arctic"%'),
                Task.payload.like('%"region":"arctic"%'),
            ),
        )
    )
    return int(result.scalar_one() or 0)


async def replenish(
    *,
    min_arctic: int,
    fill_to: int,
    dry_run: bool,
    shuffle: bool,
) -> None:
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

        aois = ARCTIC_AOIS[:]
        if shuffle:
            random.shuffle(aois)

        for i in range(need):
            aoi = aois[i % len(aois)]
            name = f"arctic-ndvi-{aoi['id']}-{i}-{int(now.timestamp())}"
            payload = make_payload(aoi, i)
            if dry_run:
                print(f"  [dry-run] {name} · {aoi['label']}")
                continue
            db.add(
                Task(
                    name=name,
                    payload=json.dumps(payload),
                    status="pending",
                    created_at=now,
                )
            )

        if not dry_run:
            await db.commit()
        print("OK replenish ártico")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--min-arctic", type=int, default=8)
    p.add_argument("--fill-to", type=int, default=20)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--no-shuffle",
        action="store_true",
        help="No barajar AOIs (orden fijo de la lista)",
    )
    args = p.parse_args()
    asyncio.run(
        replenish(
            min_arctic=args.min_arctic,
            fill_to=args.fill_to,
            dry_run=args.dry_run,
            shuffle=not args.no_shuffle,
        )
    )


if __name__ == "__main__":
    main()