"""Endpoints de tareas: descarga y envío de resultados."""
from datetime import datetime, timezone
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.db.models import Credit, Result, Task, User
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

async def _ensure_pending_tasks(db: AsyncSession, min_pending: int = 3) -> None:
    """Si hay pocas tareas pending, inserta un lote sintético (NDVI + Posidonia + fungi)."""
    from sqlalchemy import func

    count = (
        await db.execute(
            select(func.count()).select_from(Task).where(Task.status == "pending")
        )
    ).scalar() or 0
    if count >= min_pending:
        return

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    batch = []

    for i in range(3):
        batch.append(
            Task(
                name=f"ndvi-auto-{i}-{int(now.timestamp())}",
                payload=json.dumps(
                    {
                        "type": "ndvi",
                        "version": 1,
                        "tile_id": f"AUTO_NDVI_{i}",
                        "bands": {"red": 0.08 + i * 0.01, "nir": 0.36 + i * 0.02},
                        "description": "NDVI auto (API refill)",
                    }
                ),
                status="pending",
                created_at=now,
            )
        )
    for i in range(2):
        batch.append(
            Task(
                name=f"posidonia-auto-{i}-{int(now.timestamp())}",
                payload=json.dumps(
                    {
                        "type": "posidonia",
                        "version": 1,
                        "unit_id": f"POS-AUTO-{i:04d}",
                        "region": "Illes Balears",
                        "params": {"metric": "surface_m2", "method": "placeholder"},
                        "description": "Posidonia auto (API refill)",
                    }
                ),
                status="pending",
                created_at=now,
            )
        )
    for i, sp in enumerate(["Boletus edulis", "Cantharellus cibarius"]):
        slug = sp.lower().replace(" ", "-")
        batch.append(
            Task(
                name=f"fungi-auto-{slug}-{int(now.timestamp())}",
                payload=json.dumps(
                    {
                        "type": "biodiversity",
                        "subtype": "fungi",
                        "version": 1,
                        "unit_id": f"FUNGI-AUTO-{i:04d}",
                        "taxon": sp,
                        "region": "Mediterraneo",
                        "params": {"metric": "presence_score", "method": "placeholder"},
                        "description": f"Fungi auto (API refill): {sp}",
                    }
                ),
                status="pending",
                created_at=now,
            )
        )

    for t in batch:
        db.add(t)
    await db.commit()




async def _bump_expedition_progress(
    db: AsyncSession,
    task_payload: dict | str | None,
    user_id: int | None = None,
) -> dict | None:
    """Incrementa expedición activa; si se completa, desbloquea marco en el nodo del user."""
    from datetime import datetime, timezone
    from app.db.models import Expedition, Node, NodeMember

    payload = task_payload
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {}
    if not isinstance(payload, dict):
        payload = {}
    task_type = payload.get("type") or payload.get("task_type")
    if not task_type:
        return None

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = await db.execute(
        select(Expedition)
        .where(
            Expedition.is_active == True,  # noqa: E712
            Expedition.starts_at <= now,
            Expedition.ends_at >= now,
            Expedition.completed_at.is_(None),
        )
        .order_by(Expedition.starts_at.desc())
        .limit(1)
    )
    exp = result.scalar_one_or_none()
    if not exp:
        return None
    if exp.task_type and exp.task_type != task_type:
        return None

    exp.current_value = int(exp.current_value or 0) + 1
    celebration = None

    if exp.current_value >= exp.goal_value and exp.completed_at is None:
        exp.completed_at = now
        celebration = {
            "expedition_slug": exp.slug,
            "expedition_name": exp.name,
            "reward_frame": exp.reward_frame,
            "reward_badge_id": exp.reward_badge_id,
            "just_completed": True,
        }
        if user_id and exp.reward_frame:
            mem = await db.execute(
                select(NodeMember).where(NodeMember.user_id == user_id).limit(1)
            )
            membership = mem.scalar_one_or_none()
            if membership:
                node_r = await db.execute(select(Node).where(Node.id == membership.node_id))
                node = node_r.scalar_one_or_none()
                if node:
                    frames = []
                    if node.unlocked_frames:
                        try:
                            frames = json.loads(node.unlocked_frames)
                        except Exception:
                            frames = []
                    if not isinstance(frames, list):
                        frames = []
                    if exp.reward_frame not in frames:
                        frames.append(exp.reward_frame)
                        node.unlocked_frames = json.dumps(frames)
                    if not node.logo_frame:
                        node.logo_frame = exp.reward_frame
                    celebration["node_id"] = node.id
                    celebration["unlocked_frame"] = exp.reward_frame

    await db.commit()
    return celebration


@router.get("/next", response_model=TaskResponse)
async def get_next_task(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve la siguiente tarea pendiente para el usuario autenticado."""
    await _ensure_pending_tasks(db, min_pending=3)

    result = await db.execute(
        select(Task).where(Task.status == "pending").order_by(Task.id).limit(1)
    )
    task = result.scalar_one_or_none()
    if not task:
        # Último recurso (no debería ocurrir tras _ensure_pending_tasks)
        task = Task(
            name="ndvi-dummy",
            payload=json.dumps(
                {
                    "type": "ndvi",
                    "tile_id": "S2A_DUMMY",
                    "bands": {"red": 0.08, "nir": 0.42},
                    "description": "NDVI dummy fallback",
                }
            ),
            status="pending",
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

    task.status = "assigned"
    task.user_id = current_user.id
    task.assigned_at = datetime.now(timezone.utc).replace(tzinfo=None)
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
	result = await db.execute(select(Task).where(Task.id == submission.task_id))
	task = result.scalar_one_or_none()
	if not task:
		raise HTTPException(status_code=404, detail="Tarea no encontrada")
	if task.user_id != current_user.id:
		raise HTTPException(status_code=403, detail="Esta tarea no te pertenece")
	if task.status == "done":
		raise HTTPException(status_code=409, detail="Esta tarea ya fue completada")
	from app.services.validate_output import OutputValidationError, validate_output
	try:
		_payload = task.payload
		if isinstance(_payload, str):
			_payload = json.loads(_payload)
		validated = validate_output(_payload, submission.output)
	except OutputValidationError as e:
		raise HTTPException(status_code=422, detail=f"Output inválido: {e}") from e
	except Exception as e:
		raise HTTPException(status_code=422, detail=f"Output no válido: {e}") from e

	result_row = Result(
		task_id=task.id,
		output=json.dumps(validated),
		compute_time_sec=submission.compute_time_sec,
		client=submission.client,
		client_mode=submission.client_mode,
	)
	task.status = "done"
	task.completed_at = datetime.now(timezone.utc)
	# Créditos = base + bonus por tiempo (acotado)
	compute_sec = float(submission.compute_time_sec or 0.0)
	if compute_sec < 0:
		compute_sec = 0.0
	capped = min(compute_sec, settings.CREDITS_COMPUTE_CAP_SEC)
	amount = settings.CREDITS_PER_TASK + (
		settings.CREDITS_PER_COMPUTE_SEC * capped
	)
	amount = round(amount, 4)
	credit = Credit(
		user_id=current_user.id,
		task_id=task.id,
		amount=amount,
	)
	db.add(result_row)
	db.add(credit)
	await db.commit()
	await db.refresh(result_row)
	# Progreso expedición mensual (no bloquea la respuesta si falla)
	try:
		await _bump_expedition_progress(db, task.payload, user_id=current_user.id)
	except Exception:
		pass
	if isinstance(result_row.output, str):
		result_row.output = json.loads(result_row.output)
	return result_row
