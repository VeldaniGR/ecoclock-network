#!/usr/bin/env python3
"""
Seed de tareas con AOI en el Ártico (EPSG:4326).

Uso (dentro del contenedor api, con PYTHONPATH=/app):
  python /app/scripts/seed_arctic_tasks.py
  python /app/scripts/seed_arctic_tasks.py --n 20
  python /app/scripts/seed_arctic_tasks.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
from datetime import datetime, timezone

from app.db.database import AsyncSessionLocal
from app.db.models import Task

# AOIs árticas reales + nuevas repartidas para cubrir más hexágonos de la loseta
# (lat >= 60 para impact_geo). Centroides pensados para hex distintos.
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


def make_payload(aoi: dict, idx: int, jitter: float = 0.0) -> dict:
    """Payload NDVI compatible con validate_output + bbox ártico para impact_geo.
    jitter en grados mueve ligeramente el bbox para variar centroides.
    """
    j = jitter
    # pequeño desplazamiento determinista por idx para no coincidir siempre
    dj = (idx % 7 - 3) * 0.02 if jitter == 0 else 0.0
    min_lon = aoi["min_lon"] + dj - j
    max_lon = aoi["max_lon"] + dj + j
    min_lat = aoi["min_lat"] + dj - j
    max_lat = aoi["max_lat"] + dj + j
    # clamp lat al dominio ártico
    min_lat = max(60.0, min_lat)
    max_lat = min(90.0, max_lat)

    return {
        "type": "ndvi",
        "version": 1,
        "tile_id": f"ARCTIC_{aoi['id'].upper()}_{idx}",
        "datetime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cloud_cover": 12.0,
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
        "description": (
            f"NDVI / monitorización superficial — {aoi['label']} "
            "(expedición Navegantes del hielo / mapa de impacto Ártico)"
        ),
        "params": {
            "theme": "arctic_ice_melt",
            "notes": "Beta: bbox real ártico; cómputo NDVI compatible con cliente actual.",
        },
    }


async def main(n: int, dry_run: bool, shuffle: bool) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    created = 0

    aois = ARCTIC_AOIS[:]
    if shuffle:
        random.shuffle(aois)

    async with AsyncSessionLocal() as db:
        for i in range(n):
            aoi = aois[i % len(aois)]
            payload = make_payload(aoi, i)
            name = f"arctic-ndvi-{aoi['id']}-{i}-{int(now.timestamp())}"

            if dry_run:
                print(f"[dry-run] {name} · {aoi['label']}")
                print(json.dumps(payload, indent=2)[:350], "...")
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
    parser.add_argument("--n", type=int, default=20, help="Número de tareas (default 20)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--no-shuffle",
        action="store_true",
        help="No barajar AOIs (orden fijo de la lista)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.n, args.dry_run, shuffle=not args.no_shuffle))