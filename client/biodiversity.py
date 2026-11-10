# client/biodiversity.py
from __future__ import annotations
import time
from datetime import datetime, timezone
from typing import Any

import requests

GBIF_URL = "https://api.gbif.org/v1/occurrence/search"


def compute(payload: dict) -> dict[str, Any]:
    """
    Ejecuta la tarea de biodiversidad.
    En beta puede devolver un resultado simulado si falla la red.
    """
    start = time.perf_counter()
    unit_id = payload["unit_id"]
    bbox = payload["bbox"]
    params = payload.get("params", {})
    source = payload.get("source", {})

    metric = params.get("metric", "species_richness")
    limit = params.get("limit", 300)
    max_records = params.get("max_records", 3000)
    year_from = source.get("year_from", 2015)
    year_to = source.get("year_to", 2024)

    species = set()
    total_occ = 0
    offset = 0

    try:
        while total_occ < max_records:
            query = {
                "country": source.get("country", "ES"),
                "decimalLongitude": f"{bbox['min_lon']},{bbox['max_lon']}",
                "decimalLatitude": f"{bbox['min_lat']},{bbox['max_lat']}",
                "hasCoordinate": "true",
                "year": f"{year_from},{year_to}",
                "limit": limit,
                "offset": offset,
            }
            r = requests.get(GBIF_URL, params=query, timeout=30)
            r.raise_for_status()
            data = r.json()

            results = data.get("results", [])
            if not results:
                break

            for rec in results:
                # preferimos scientificName o species
                name = rec.get("species") or rec.get("scientificName")
                if name:
                    species.add(name.strip())
                total_occ += 1

            if data.get("endOfRecords") or len(results) < limit:
                break
            offset += limit

        value = len(species) if metric == "species_richness" else total_occ

    except Exception as e:
        # Fallback simulado (beta)
        print(f"[biodiversity] fallback por error: {e}")
        value = 120 + (hash(unit_id) % 400)   # valor determinista fake
        total_occ = value * 4
        metric = metric + "_simulated"

    elapsed = time.perf_counter() - start

    return {
        "type": "biodiversity",
        "version": 1,
        "unit_id": unit_id,
        "metric": metric,
        "value": value,
        "unit": "species" if "richness" in metric else "occurrences",
        "occurrence_count": total_occ,
        "method": params.get("method", "occurrence_count"),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "compute_time_sec": round(elapsed, 2),
    }
