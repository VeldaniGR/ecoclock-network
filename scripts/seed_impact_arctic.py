#!/usr/bin/env python3
"""Seed: loseta de impacto Ártico + expedición de invierno."""
import asyncio
from datetime import datetime

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import ImpactTile, Expedition


async def main() -> None:
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(ImpactTile).where(ImpactTile.slug == "arctic"))
        if r.scalar_one_or_none():
            print("ImpactTile arctic ya existe")
        else:
            tile = ImpactTile(
                slug="arctic",
                name="Artico",
                description=(
                    "Loseta del mapa de impacto centrada en el Artico. "
                    "Hexagonos desbloqueados por tareas o por la expedicion "
                    "Navegantes del hielo."
                ),
            )
            db.add(tile)
            print("OK: ImpactTile arctic creada")

        r2 = await db.execute(
            select(Expedition).where(Expedition.slug == "arctic-winter-2026")
        )
        if r2.scalar_one_or_none():
            print("Expedicion arctic-winter-2026 ya existe")
        else:
            exp = Expedition(
                slug="arctic-winter-2026",
                name="Navegantes del hielo",
                description=(
                    "Expedicion de invierno: monitorizacion del deshielo artico. "
                    "Completa tareas y la actividad exterior con el cuadrante "
                    "para ganar el logro y colorear hexagonos en la loseta Artico."
                ),
                task_type=None,
                goal_value=300,
                current_value=0,
                reward_frame="arctic_ice",
                reward_badge_id="exp_arctic_winter_2026",
                starts_at=datetime(2026, 11, 1, 0, 0, 0),
                ends_at=datetime(2027, 2, 28, 23, 59, 59),
                is_active=True,
            )
            db.add(exp)
            print("OK: expedicion arctic-winter-2026 creada")

        await db.commit()
        print("Seed finalizado")


if __name__ == "__main__":
    asyncio.run(main())
