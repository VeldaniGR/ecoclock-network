#!/usr/bin/env python3
"""
Seed de tareas de biodiversidad (GBIF) → tabla tasks (pending).

Uso:
  python scripts/seed_gbif_tasks.py --n 10
  python scripts/seed_gbif_tasks.py --n 5 --dry-run
  python scripts/seed_gbif_tasks.py --region valencia --n 8
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.models import Task
from app.core.config import settings

# ──────────────────────────────────────────────────────────────
# AOIs de ejemplo (grids de ~1° o zonas de interés)
# ──────────────────────────────────────────────────────────────
AOIS = {
    "valencia": {
        "min_lon": -0.8, "min_lat": 38.7,
        "max_lon":  0.3, "max_lat": 39.7,
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

GBIF_OCCURRENCE = "https://api.gbif.org/v1/occurrence/search"


def make_biodiversity_payload(aoi: dict, idx: int, year_from: int = 2015, year_to: int = 2024) -> dict:
    """Payload ligero. El cliente hará la consulta real a GBIF."""
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
            "limit": 300,          # límite por página que usará el cliente
            "max_records": 3000,   # tope total para no saturar
        },
        "description": (
            f"Calcular riqueza de especies a partir de ocurrencias GBIF "
            f"en {aoi['label']} ({year_from}-{year_to})."
        ),
    }


async def insert_tasks(session: AsyncSession, payloads: list[tuple[str, dict]], dry_run: bool) -> int:
    created = 0
    for name, payload in payloads:
        if dry_run:
            print(f"[dry-run] {name}")
            print(json.dumps(payload, indent=2)[:300] + "...\n")
            created += 1
            continue
        task = Task(
            name=name,
            payload=json.dumps(payload),
            status="pending",
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(task)
        created += 1
    if not dry_run:
        await session.commit()
    return created


async def main(n: int, region: str, dry_run: bool):
    if region not in AOIS:
        print(f"Región '{region}' no definida. Disponibles: {list(AOIS.keys())}")
        sys.exit(1)

    aoi = AOIS[region]
    print(f"🌱 Generando {n} tareas de biodiversidad para: {aoi['label']}")

    payloads: list[tuple[str, dict]] = []
    for i in range(n):
        pl = make_biodiversity_payload(aoi, i)
        name = f"biodiversity-{pl['unit_id']}"
        payloads.append((name, pl))

    # ── Insertar en DB ────────────────────────────────────────
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        created = await insert_tasks(session, payloads, dry_run)

    print(f"\n✅ {'(dry-run) ' if dry_run else ''}{created} tareas preparadas.")
    if not dry_run:
        print("   Ahora cualquier cliente puede hacer GET /tasks/next")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed tareas GBIF → Eco'clock")
    parser.add_argument("--n", type=int, default=5, help="Número de tareas")
    parser.add_argument("--region", default="valencia", choices=list(AOIS.keys()))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    asyncio.run(main(args.n, args.region, args.dry_run))
