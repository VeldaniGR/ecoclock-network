#!/usr/bin/env python3
"""
Fase C — Seed de tareas Copernicus (NDVI + Posidonia) → tabla tasks (pending).

Uso:
  python scripts/seed_copernicus_tasks.py --ndvi 5 --posidonia 5
  python scripts/seed_copernicus_tasks.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Añadir raíz del repo al path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import httpx
from pystac_client import Client
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.models import Task
from app.core.config import settings
from app.services.copernicus import get_cdse_token, cdse_auth_headers

# ──────────────────────────────────────────────────────────────
# AOIs de ejemplo (EPSG:4326)
# ──────────────────────────────────────────────────────────────
AOI_NDVI = {          # Ejemplo: zona mediterránea / deforestación ligera
    "min_lon": -0.5, "min_lat": 38.5,
    "max_lon":  0.5, "max_lat": 39.5,
    "crs": "EPSG:4326",
    "label": "Valencia-Alicante (NDVI demo)",
}

AOI_POSIDONIA = {     # Illes Balears (Atlas Posidonia)
    "min_lon": 2.3,  "min_lat": 39.3,
    "max_lon": 3.5,  "max_lat": 40.1,
    "crs": "EPSG:4326",
    "label": "Illes Balears",
}

STAC_URL = "https://stac.dataspace.copernicus.eu/v1"
COLLECTION = "sentinel-2-l2a"


def search_stac(bbox: dict, days_back: int = 30, max_items: int = 10) -> list:
    """Busca ítems Sentinel-2 L2A recientes con baja nubosidad."""
    client = Client.open(STAC_URL)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)

    search = client.search(
        collections=[COLLECTION],
        bbox=[bbox["min_lon"], bbox["min_lat"], bbox["max_lon"], bbox["max_lat"]],
        datetime=f"{start.isoformat()}/{end.isoformat()}",
        query={"eo:cloud_cover": {"lt": 30}},
        max_items=max_items,
    )
    return list(search.items())


def make_ndvi_payload(item, idx: int) -> dict:
    """Payload ligero NDVI (beta: sin raster completo)."""
    props = item.properties or {}
    return {
        "type": "ndvi",
        "version": 1,
        "tile_id": item.id,
        "datetime": props.get("datetime"),
        "cloud_cover": props.get("eo:cloud_cover"),
        "bbox": {
            "min_lon": item.bbox[0], "min_lat": item.bbox[1],
            "max_lon": item.bbox[2], "max_lat": item.bbox[3],
            "crs": "EPSG:4326",
        },
        "bands": {          # valores de ejemplo / placeholder para cálculo local
            "red": 0.08 + (idx % 10) * 0.01,
            "nir": 0.35 + (idx % 10) * 0.02,
        },
        "source": {
            "name": "copernicus_cdse",
            "collection": COLLECTION,
            "stac_id": item.id,
        },
        "description": f"Calcular NDVI sobre escena Sentinel-2 {item.id}",
    }


def make_posidonia_payload(item, idx: int) -> dict:
    """Payload según tasks/posidonia/README.md."""
    unit_id = f"POS-BAL-{datetime.now().year}-T{idx:04d}"
    return {
        "type": "posidonia",
        "version": 1,
        "unit_id": unit_id,
        "region": "Illes Balears",
        "bbox": {
            "min_lon": item.bbox[0], "min_lat": item.bbox[1],
            "max_lon": item.bbox[2], "max_lat": item.bbox[3],
            "crs": "EPSG:4326",
        },
        "source": {
            "name": "copernicus_cdse",
            "collection": COLLECTION,
            "stac_id": item.id,
            "url": "https://atlasposidonia.com/es",
            "year": datetime.now().year,
        },
        "params": {
            "metric": "surface_m2",
            "method": "placeholder",
            "notes": "Beta: cliente puede devolver resultado simulado coherente.",
        },
        "description": f"Estimar superficie de Posidonia oceanica — unidad {unit_id}",
    }


async def insert_tasks(session: AsyncSession, payloads: list[tuple[str, dict]], dry_run: bool):
    created = 0
    for name, payload in payloads:
        if dry_run:
            print(f"[dry-run] {name} → {json.dumps(payload, indent=2)[:200]}...")
            created += 1
            continue
        from datetime import datetime, timezone
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


async def main(ndvi_n: int, posidonia_n: int, dry_run: bool):
    print("🔑 Obteniendo token CDSE...")
    try:
        token = get_cdse_token()
        print("   Token OK")
    except Exception as e:
        print(f"⚠️  No se pudo obtener token CDSE ({e}). Continuamos con payloads sintéticos.")
        token = None

    payloads: list[tuple[str, dict]] = []

    # ── NDVI ──────────────────────────────────────────────────
    print(f"\n📡 Buscando escenas NDVI (máx {ndvi_n})...")
    try:
        items = search_stac(AOI_NDVI, max_items=ndvi_n) if token else []
    except Exception as e:
        print(f"   STAC falló ({e}). Usando sintéticos.")
        items = []

    for i in range(ndvi_n):
        if i < len(items):
            pl = make_ndvi_payload(items[i], i)
        else:
            # Fallback sintético
            pl = {
                "type": "ndvi",
                "version": 1,
                "tile_id": f"S2A_SYNTH_{i:04d}",
                "bands": {"red": 0.08, "nir": 0.42},
                "description": "NDVI sintético (fallback)",
            }
        payloads.append((f"ndvi-{pl.get('tile_id', i)}", pl))

    # ── Posidonia ─────────────────────────────────────────────
    print(f"\n🪸 Buscando escenas Posidonia (máx {posidonia_n})...")
    try:
        items = search_stac(AOI_POSIDONIA, max_items=posidonia_n) if token else []
    except Exception as e:
        print(f"   STAC falló ({e}). Usando sintéticos.")
        items = []

    for i in range(posidonia_n):
        if i < len(items):
            pl = make_posidonia_payload(items[i], i)
        else:
            pl = {
                "type": "posidonia",
                "version": 1,
                "unit_id": f"POS-BAL-2026-T{i:04d}",
                "region": "Illes Balears",
                "bbox": AOI_POSIDONIA,
                "params": {"metric": "surface_m2", "method": "placeholder"},
                "description": "Posidonia sintética (fallback)",
            }
        payloads.append((f"posidonia-{pl['unit_id']}", pl))

    # ── Insertar en DB ────────────────────────────────────────
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        n = await insert_tasks(session, payloads, dry_run)

    print(f"\n✅ {'(dry-run) ' if dry_run else ''}{n} tareas preparadas.")
    if not dry_run:
        print("   Ahora cualquier cliente (CLI / GUI / APK) puede hacer GET /tasks/next")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed tareas Copernicus → Eco'clock")
    parser.add_argument("--ndvi", type=int, default=5, help="Número de tareas NDVI")
    parser.add_argument("--posidonia", type=int, default=5, help="Número de tareas Posidonia")
    parser.add_argument("--dry-run", action="store_true", help="No escribe en DB")
    args = parser.parse_args()

    asyncio.run(main(args.ndvi, args.posidonia, args.dry_run))
