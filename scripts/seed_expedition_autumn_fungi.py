"""Seed: Expedición Otoño · Hongos (octubre). Ejecutar dentro del contenedor o venv."""
import asyncio
from datetime import datetime

from sqlalchemy import select

from app.db.database import async_session_maker
from app.db.models import Expedition


async def main() -> None:
    async with async_session_maker() as db:
        r = await db.execute(select(Expedition).where(Expedition.slug == "autumn-fungi-2026"))
        if r.scalar_one_or_none():
            print("Ya existe autumn-fungi-2026")
            return

        e = Expedition(
            slug="autumn-fungi-2026",
            name="Expedición Otoño · Hongos",
            description=(
                "Temporada de hongos: la red se une para completar tareas de biodiversidad "
                "(biodiversity). Meta colectiva del mes."
            ),
            task_type="biodiversity",
            goal_value=500,  # ajustar a tu ritmo real
            current_value=0,
            reward_frame="autumn_fungi",
            reward_badge_id="exp_autumn_fungi_2026",
            starts_at=datetime(2026, 10, 1, 0, 0, 0),
            ends_at=datetime(2026, 10, 31, 23, 59, 59),
            is_active=True,
        )
        db.add(e)
        await db.commit()
        print("OK: expedición autumn-fungi-2026 creada")


if __name__ == "__main__":
    asyncio.run(main())
