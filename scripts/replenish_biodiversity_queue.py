#!/usr/bin/env python3
"""Reposición de cola biodiversity."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from dotenv import load_dotenv
load_dotenv(ROOT / "server" / ".env")
load_dotenv(ROOT / ".env")

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models import Task

AOIS = {
    "valencia": {
        "min_lon": -0.8, "min_lat": 38.7,
        "max_lon": 0.3, "max_lat": 39.7,
        "label": "Comunidad Valenciana (demo)",
        "prefix": "BIO-VAL",
    },
    "baleares": {
        "min_lon": 2.3, "min_lat": 39.3,
        "max_lon": 3.5, "max_lat": 40.1,
        "label": "Illes Balears",
        "prefix": "BIO-BAL",
    },
    "andalucia_este": {
        "min_lon": -3.5, "min_lat": 36.5,
        "max_lon": -1.5, "max_lat": 38.0,
        "label": "Andalucía oriental",
        "prefix": "BIO-AND",
    },
    "galicia": {
        "min_lon": -9.3, "min_lat": 41.8,
        "max_lon": -6.8, "max_lat": 43.8,
        "label": "Galicia",
        "prefix": "BIO-GAL",
    },
}


def make_payload(aoi: dict, idx: int, year_from: int = 2015, year_to: int = 2024) -> dict:
    unit_id = f"{aoi['prefix']}-{year_to}-T{idx:04d}"
    return {
        "type": "biodiversity",
        "version": 1,
        "unit_id": unit_id,
        "region": aoi["label"],
        "bbox": {
            "min_lon": aoi["min_lon"],
            "min_lat": aoi["min_lat"],
            "max_lon": aoi["max_lon"],
            "max_lat": aoi["max_lat"],
            "crs": "EPSG:4326",
        },
        "source": {
            "name": "gbif",
            "api": "https://api.gbif.org/v1",
            "country": "ES",
            "year_from": year_from,
            "year_to": year_to,
        },
        "params": {
            "metric": "species_richness",
            "method": "occurrence_count",
            "has_coordinate": True,
            "limit": 300,
        },
        "description": "Calcular riqueza de especies (GBIF) en la celda indicada.",
    }


def _db_url() -> str:
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


async def count_pending(session: AsyncSession) -> int:
    r = await session.execute(
        select(func.count()).select_from(Task).where(Task.status == "pending")
    )
    return int(r.scalar_one() or 0)


async def existing_names(session: AsyncSession) -> set[str]:
    r = await session.execute(select(Task.name))
    return {row[0] for row in r.all()}


async def run(*, min_pending: int, fill_to: int, region: str, dry_run: bool) -> None:
    if region not in AOIS:
        raise SystemExit(f"Región desconocida: {region}. Opciones: {list(AOIS)}")
    aoi = AOIS[region]
    if fill_to < min_pending:
        fill_to = min_pending

    engine = create_async_engine(_db_url(), echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        pending = await count_pending(session)
        print(f"Pending: {pending} (min={min_pending}, fill_to={fill_to}, region={region})")
        if pending >= min_pending:
            print("Cola suficiente.")
            await engine.dispose()
            return

        need = fill_to - pending
        known = await existing_names(session)
        created = 0
        start_idx = 10_000
        for i in range(start_idx, start_idx + need + 50):
            if created >= need:
                break
            payload = make_payload(aoi, i)
            name = f"biodiversity-{payload['unit_id']}"
            if name in known:
                continue
            if dry_run:
                print(f"  [dry-run] {name}")
            else:
                session.add(
                    Task(name=name, payload=json.dumps(payload), status="pending")
                )
                print(f"  + {name}")
            known.add(name)
            created += 1

        if not dry_run and created:
            await session.commit()
        print(f"{'Dry-run:' if dry_run else 'Creadas'} {created} tarea(s) biodiversity.")

    await engine.dispose()


def main() -> None:
    p = argparse.ArgumentParser(description="Reponer cola biodiversity")
    p.add_argument("--min-pending", type=int, default=5)
    p.add_argument("--fill-to", type=int, default=15)
    p.add_argument("--region", default="valencia", choices=list(AOIS.keys()))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    asyncio.run(
        run(
            min_pending=args.min_pending,
            fill_to=args.fill_to,
            region=args.region,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
