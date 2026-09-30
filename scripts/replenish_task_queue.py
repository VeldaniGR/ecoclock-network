#!/usr/bin/env python3
"""
Reposición automática de la cola de tareas (posidonia vía CDSE STAC).

Si hay menos de --min-pending tareas pending, crea hasta llegar a --fill-to.

Uso (desde server/, venv activo, Postgres arriba):

  cd ~/Projects/ecoclock-network/server
  source .venv/bin/activate
  export PYTHONPATH=.

  python ../scripts/replenish_task_queue.py
  python ../scripts/replenish_task_queue.py --min-pending 5 --fill-to 15
  python ../scripts/replenish_task_queue.py --dry-run

Cron local (cada 15 min):

  */15 * * * * cd /home/TU_USER/Projects/ecoclock-network/server && . .venv/bin/activate && PYTHONPATH=. python ../scripts/replenish_task_queue.py --min-pending 5 --fill-to 15 >> /tmp/ecoclock-replenish.log 2>&1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

from sqlalchemy import func, select

from app.db.database import AsyncSessionLocal
from app.db.models import Task
from app.services.copernicus import (
    build_posidonia_payload,
    search_sentinel2_l2a,
)

DEFAULT_BBOX = [2.65, 39.50, 2.75, 39.58]
DEFAULT_DATETIME = "2024-06-01T00:00:00Z/2024-09-30T23:59:59Z"


async def count_pending(db) -> int:
    result = await db.execute(
        select(func.count()).select_from(Task).where(Task.status == "pending")
    )
    return int(result.scalar_one() or 0)


async def existing_task_names(db) -> set[str]:
    result = await db.execute(select(Task.name))
    return {row[0] for row in result.all()}


async def replenish(
    *,
    min_pending: int,
    fill_to: int,
    bbox: list[float],
    datetime_range: str,
    max_cloud: float,
    stac_limit: int,
    dry_run: bool,
) -> None:
    if fill_to < min_pending:
        print("Aviso: --fill-to < --min-pending; se usará fill_to = min_pending")
        fill_to = min_pending

    async with AsyncSessionLocal() as db:
        pending = await count_pending(db)
        print(f"Pending actuales: {pending} (umbral={min_pending}, objetivo={fill_to})")

        if pending >= min_pending:
            print("Cola suficiente. No se crea nada.")
            return

        need = fill_to - pending
        print(f"Faltan ~{need} tarea(s). Buscando en STAC (limit={stac_limit})...")

        items = search_sentinel2_l2a(
            bbox=bbox,
            datetime_range=datetime_range,
            max_cloud=max_cloud,
            limit=max(stac_limit, need),
        )
        if not items:
            print("STAC no devolvió escenas. Prueba ampliar fechas o max_cloud.")
            return

        print(f"STAC: {len(items)} escena(s)")
        known = await existing_task_names(db)
        created = 0

        for it in items:
            if created >= need:
                break
            product_id = it.get("id") or "UNKNOWN"
            name = f"posidonia-{product_id[:40]}"
            if name in known:
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

            if dry_run:
                print(f"  [dry-run] crearía: {name}")
                created += 1
                known.add(name)
                continue

            task = Task(
                name=name,
                payload=json.dumps(payload),
                status="pending",
            )
            db.add(task)
            known.add(name)
            created += 1
            print(f"  + {name}")

        if not dry_run and created:
            await db.commit()

        print(
            f"{'Dry-run: se crearían' if dry_run else 'Creadas'} {created} tarea(s). "
            f"Pending estimado ≈ {pending + created}."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reponer cola de tareas posidonia si pending < umbral"
    )
    parser.add_argument(
        "--min-pending",
        type=int,
        default=5,
        help="Si pending < este valor, se rellena (default 5)",
    )
    parser.add_argument(
        "--fill-to",
        type=int,
        default=15,
        help="Objetivo de tareas pending tras reponer (default 15)",
    )
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        default=DEFAULT_BBOX,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
    )
    parser.add_argument("--datetime", default=DEFAULT_DATETIME, dest="datetime_range")
    parser.add_argument("--max-cloud", type=float, default=30.0)
    parser.add_argument(
        "--stac-limit",
        type=int,
        default=20,
        help="Máx. escenas a pedir a STAC por pasada",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo informa; no escribe en BD",
    )
    args = parser.parse_args()

    asyncio.run(
        replenish(
            min_pending=args.min_pending,
            fill_to=args.fill_to,
            bbox=list(args.bbox),
            datetime_range=args.datetime_range,
            max_cloud=args.max_cloud,
            stac_limit=args.stac_limit,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
