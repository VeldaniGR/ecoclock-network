#!/usr/bin/env python3
"""
Fase C — Busca Sentinel-2 L2A (CDSE STAC) sobre Baleares y crea Task(s) posidonia.

Uso (desde server/, con venv activo y Postgres arriba):

  cd ~/Projects/ecoclock-network/server
  source .venv/bin/activate
  export PYTHONPATH=.
  python ../scripts/seed_posidonia_tasks.py
  python ../scripts/seed_posidonia_tasks.py --dry-run
  python ../scripts/seed_posidonia_tasks.py --limit 3 --max-cloud 20

Requisitos: CDSE_USERNAME/PASSWORD en server/.env y get_cdse_token funcionando.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Permitir importar app.* si se ejecuta desde scripts/
ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Task
from app.services.copernicus import (
    build_posidonia_payload,
    search_sentinel2_l2a,
)

# Zona por defecto ≈ costa Mallorca (Browser: lat 39.544, lng 2.697)
DEFAULT_BBOX = [2.65, 39.50, 2.75, 39.58]  # min_lon, min_lat, max_lon, max_lat
DEFAULT_DATETIME = "2024-06-01T00:00:00Z/2024-09-30T23:59:59Z"


async def seed(
    *,
    bbox: list[float],
    datetime_range: str,
    max_cloud: float,
    limit: int,
    dry_run: bool,
) -> None:
    print(f"STAC search bbox={bbox} datetime={datetime_range} max_cloud={max_cloud}")
    items = search_sentinel2_l2a(
        bbox=bbox,
        datetime_range=datetime_range,
        max_cloud=max_cloud,
        limit=limit,
    )
    if not items:
        print("No se encontraron escenas. Prueba ampliar fechas o max_cloud.")
        return

    print(f"Encontradas {len(items)} escena(s):")
    for i, it in enumerate(items, 1):
        print(
            f"  {i}. {it['id']}  clouds={it.get('cloud_cover')}  "
            f"date={it.get('datetime')}"
        )

    if dry_run:
        print("Dry-run: no se escribe en BD.")
        payload = build_posidonia_payload(
            product_id=items[0]["id"] or "UNKNOWN",
            bbox=bbox,
            cloud_cover=items[0].get("cloud_cover"),
            datetime_str=items[0].get("datetime"),
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    created = 0
    async with AsyncSessionLocal() as db:
        for it in items:
            product_id = it.get("id") or "UNKNOWN"
            # Evitar duplicar por product_id en name
            name = f"posidonia-{product_id[:40]}"
            existing = await db.execute(select(Task).where(Task.name == name))
            if existing.scalar_one_or_none():
                print(f"  skip (ya existe): {name}")
                continue

            item_bbox = it.get("bbox") or bbox
            if len(item_bbox) != 4:
                item_bbox = bbox

            payload = build_posidonia_payload(
                product_id=product_id,
                bbox=list(item_bbox),
                cloud_cover=it.get("cloud_cover"),
                datetime_str=it.get("datetime"),
            )
            task = Task(
                name=name,
                payload=json.dumps(payload),
                status="pending",
            )
            db.add(task)
            created += 1

        await db.commit()

    print(f"Creadas {created} tarea(s) pending. GET /tasks/next las asignará.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed tareas posidonia desde CDSE")
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        default=DEFAULT_BBOX,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
    )
    parser.add_argument("--datetime", default=DEFAULT_DATETIME, dest="datetime_range")
    parser.add_argument("--max-cloud", type=float, default=30.0)
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo busca STAC; no inserta en BD",
    )
    args = parser.parse_args()

    asyncio.run(
        seed(
            bbox=list(args.bbox),
            datetime_range=args.datetime_range,
            max_cloud=args.max_cloud,
            limit=args.limit,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
