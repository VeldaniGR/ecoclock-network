#!/usr/bin/env python3
"""
Devuelve a la cola (pending) las tareas que se asignaron pero nunca se enviaron.

Una tarea queda en 'assigned' cuando un cliente la pide (/tasks/next) y no llega a
enviar el resultado (cierre de la app, fallo de red...). Sin este paso no vuelve
a la cola.

Solo toca tareas en 'assigned' desde hace más de --hours horas (o sin fecha de
asignación) y que no tengan ningún resultado guardado. Es idempotente: se puede
ejecutar cuantas veces haga falta.

Uso (dentro del contenedor api, con PYTHONPATH=/app):
  python /app/scripts/requeue_stale_tasks.py --dry-run
  python /app/scripts/requeue_stale_tasks.py --hours 6

Cron (cada hora, ejemplo en el host):
  15 * * * * cd /opt/ecoclock-network && docker compose exec -T -e PYTHONPATH=/app api \
    python /app/scripts/requeue_stale_tasks.py --hours 6 \
    >> /var/log/ecoclock-requeue.log 2>&1
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, literal_column, or_, select, update

from app.db.database import AsyncSessionLocal
from app.db.models import Result, Task


async def main(hours: float, dry_run: bool) -> None:
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)

    stale = and_(
        Task.status == "assigned",
        or_(Task.assigned_at.is_(None), Task.assigned_at < cutoff),
        # Por si hubiera una tarea incoherente con resultado ya guardado: no se toca
        ~select(Result.id).where(Result.task_id == Task.id).exists(),
    )
    # Tipo = prefijo del nombre (arctic, fungi, ndvi, posidonia). Las constantes van
    # escritas en el SQL para que SELECT y GROUP BY sean la misma expresión.
    tipo = func.split_part(Task.name, literal_column("'-'"), literal_column("1"))

    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(
                    tipo.label("tipo"),
                    func.count(),
                    func.min(Task.assigned_at),
                    func.max(Task.assigned_at),
                )
                .where(stale)
                .group_by(tipo)
                .order_by(tipo)
            )
        ).all()

        total = sum(r[1] for r in rows)
        print(f"Tareas atascadas (assigned hace más de {hours:g} h): {total}")
        for t, n, oldest, newest in rows:
            print(f"  {t:<10} {n:>6}   asignadas entre {oldest} y {newest}")

        if dry_run:
            print("(dry-run) No se ha cambiado nada")
            return
        if total == 0:
            print("Nada que devolver a la cola")
            return

        result = await db.execute(
            update(Task)
            .where(stale)
            .values(status="pending", user_id=None, assigned_at=None)
        )
        await db.commit()
        print(f"OK: {result.rowcount} tareas devueltas a la cola")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Devolver a la cola tareas asignadas y nunca enviadas")
    parser.add_argument("--hours", type=float, default=6.0, help="antigüedad mínima de la asignación (default 6)")
    parser.add_argument("--dry-run", action="store_true", help="solo muestra qué haría")
    args = parser.parse_args()
    asyncio.run(main(args.hours, args.dry_run))
