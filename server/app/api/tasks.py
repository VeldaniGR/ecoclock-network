"""Endpoints de tareas: descarga y envío de resultados."""
from datetime import datetime, timezone
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.db.models import Result, Task, User
from app.schemas.task import ResultResponse, TaskResponse, TaskSubmit

router = APIRouter()


async def _create_dummy_ndvi_task(db: AsyncSession) -> Task:
    """Crea una tarea dummy de cálculo NDVI si no hay tareas pendientes."""
    payload = {
        "type": "ndvi",
        "tile_id": "S2A_MSIL1C_20250615_T31TGL",
        "bands": {
            "red": 0.08,
            "nir": 0.42,
        },
        "description": "Calcular NDVI (Normalized Difference Vegetation Index) sobre una imagen Sentinel-2 simulada.",
    }
    task = Task(name="ndvi-dummy", payload=json.dumps(payload), status="pending")
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/next", response_model=TaskResponse)
async def get_next_task(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve la siguiente tarea pendiente para el usuario autenticado."""
    task = result = await db.execute(select(Task).where(Task.status == "pending")); task = result.scalar_one_or_none()
    if not task:
        task = await _create_dummy_ndvi_task(db)

    task.status = "assigned"
    task.user_id = current_user.id
    task.assigned_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)

    if isinstance(task.payload, str):
        task.payload = json.loads(task.payload)

    return task


@router.post("/submit", response_model=ResultResponse, status_code=201)
async def submit_result(
    submission: TaskSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recibe el resultado de una tarea procesada por el cliente."""
    task = result = await db.execute(select(Task).where(Task.id == submission.task_id)); task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Esta tarea no te pertenece")
    if task.status == "done":
        raise HTTPException(status_code=409, detail="Esta tarea ya fue completada")

    result = Result(
        task_id=task.id,
        output=json.dumps(submission.output),
        compute_time_sec=submission.compute_time_sec,
    )
    task.status = "done"
    task.completed_at = datetime.now(timezone.utc)
    db.add(result)
    await db.commit()
    await db.refresh(result)

    if isinstance(result.output, str):
        result.output = json.loads(result.output)

    return result
