#!/usr/bin/env python3
"""
Seed de tareas con AOI en el Ártico (EPSG:4326).

Uso (dentro del contenedor api, con PYTHONPATH=/app):
  python /app/scripts/seed_arctic_tasks.py
  python /app/scripts/seed_arctic_tasks.py --n 5
  python /app/scripts/seed_arctic_tasks.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

from app.db.database import AsyncSessionLocal
from app.db.models import Task

# AOIs árticas reales (aprox.) — todas con lat >= 60 para impact_geo
ARCTIC_AOIS = [
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
        "label": "Rusia · Severnaya Zemlya (aprox.)",
        "min_lon": 95.0, "min_lat": 78.0,
        "max_lon": 100.0, "max_lat": 80.0,
    },
]


def make_payload(aoi: dict, idx: int) -> dict:
    """Payload NDVI compatible con validate_output + bbox ártico para impact_geo."""
    return {
        "type": "ndvi",
        "version": 1,
        "tile_id": f"ARCTIC_{aoi['id'].upper()}_{idx}",
        "datetime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cloud_cover": 12.0,
        "bbox": {
            "min_lon": aoi["min_lon"],
            "min_lat": aoi["min_lat"],
            "max_lon": aoi["max_lon"],
            "max_lat": aoi["max_lat"],
            "crs": "EPSG:4326",
        },
        "aoi_label": aoi["label"],
        "region": "arctic",
        "bands": {
            "red": 0.04 + (idx % 5) * 0.01,
            "nir": 0.18 + (idx % 5) * 0.02,
        },
        "description": (
            f"NDVI / monitorización superficial — {aoi['label']} "
            "(expedición Navegantes del hielo / mapa de impacto Ártico)"
        ),
        "params": {
            "theme": "arctic_ice_melt",
            "notes": "Beta: bbox real ártico; cómputo NDVI compatible con cliente actual.",
        },
    }


async def main(n: int, dry_run: bool) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    created = 0

    async with AsyncSessionLocal() as db:
        for i in range(n):
            aoi = ARCTIC_AOIS[i % len(ARCTIC_AOIS)]
            payload = make_payload(aoi, i)
            name = f"arctic-ndvi-{aoi['id']}-{i}-{int(now.timestamp())}"

            if dry_run:
                print(f"[dry-run] {name}")
                print(json.dumps(payload, indent=2)[:400], "...")
                created += 1
                continue

            task = Task(
                name=name,
                payload=json.dumps(payload),
                status="pending",
                created_at=now,
            )
            db.add(task)
            created += 1

        if not dry_run:
            await db.commit()

    print(f"OK: {created} tareas árticas {'(dry-run)' if dry_run else 'insertadas'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed tareas Ártico")
    parser.add_argument("--n", type=int, default=8, help="Número de tareas (default 8)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.n, args.dry_run))
