"""Endpoints de Nodos Ciudadanos."""
import secrets
import string
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user
from app.db.database import get_db
from app.db.models import User, Node, NodeMember, NodeJoinRequest
from app.schemas.node import (
    NodeCreate,
    NodePublic,
    NodeDetail,
    NodeMemberOut,
    JoinRequestOut,
    TransferLeadership,
)

router = APIRouter()


def _generate_invite_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _get_user_node(db: AsyncSession, user_id: int) -> NodeMember | None:
    result = await db.execute(
        select(NodeMember)
        .where(NodeMember.user_id == user_id)
        .options(selectinload(NodeMember.node))
    )
    return result.scalar_one_or_none()


@router.post("", response_model=NodeDetail, status_code=status.HTTP_201_CREATED)
async def create_node(
    payload: NodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Un usuario solo puede estar en un nodo
    existing = await _get_user_node(db, current_user.id)
    if existing:
        raise HTTPException(status_code=400, detail="Ya perteneces a un nodo. Debes salir primero.")

    # Generar código único
    for _ in range(10):
        code = _generate_invite_code()
        check = await db.execute(select(Node).where(Node.invite_code == code))
        if not check.scalar_one_or_none():
            break
    else:
        raise HTTPException(status_code=500, detail="No se pudo generar código único")

    node = Node(
        name=payload.name.strip(),
        invite_code=code,
        created_by=current_user.id,
        member_count=1,
        is_public=True,
    )
    db.add(node)
    await db.flush()

    member = NodeMember(
        node_id=node.id,
        user_id=current_user.id,
        role="admin",
    )
    db.add(member)
    await db.commit()
    await db.refresh(node)

    return NodeDetail(
        id=node.id,
        name=node.name,
        logo_url=node.logo_url,
        member_count=node.member_count,
        is_public=node.is_public,
        invite_code=node.invite_code,
        created_at=node.created_at,
        my_role="admin",
    )


@router.get("/me", response_model=NodeDetail)
async def get_my_node(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = await _get_user_node(db, current_user.id)
    if not membership:
        raise HTTPException(status_code=404, detail="No perteneces a ningún nodo")

    node = membership.node
    return NodeDetail(
        id=node.id,
        name=node.name,
        logo_url=node.logo_url,
        member_count=node.member_count,
        is_public=node.is_public,
        invite_code=node.invite_code if membership.role == "admin" else "",  # solo admin ve el código
        created_at=node.created_at,
        my_role=membership.role,
    )


@router.get("", response_model=list[NodePublic])
async def list_public_nodes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listado parcial: nombre + member_count + logo (sin código ni miembros)."""
    result = await db.execute(
        select(Node).where(Node.is_public == True).order_by(Node.member_count.desc())
    )
    nodes = result.scalars().all()
    return nodes


@router.post("/join/{code}", response_model=NodeDetail)
async def join_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await _get_user_node(db, current_user.id)
    if existing:
        raise HTTPException(status_code=400, detail="Ya perteneces a un nodo")

    result = await db.execute(select(Node).where(Node.invite_code == code.upper()))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Código de invitación inválido")

    member = NodeMember(node_id=node.id, user_id=current_user.id, role="member")
    node.member_count += 1
    db.add(member)
    await db.commit()
    await db.refresh(node)

    return NodeDetail(
        id=node.id,
        name=node.name,
        logo_url=node.logo_url,
        member_count=node.member_count,
        is_public=node.is_public,
        invite_code="",
        created_at=node.created_at,
        my_role="member",
    )


@router.post("/{node_id}/request", status_code=status.HTTP_201_CREATED)
async def request_join(
    node_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await _get_user_node(db, current_user.id)
    if existing:
        raise HTTPException(status_code=400, detail="Ya perteneces a un nodo")

    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if not node or not node.is_public:
        raise HTTPException(status_code=404, detail="Nodo no encontrado")

    # Evitar solicitudes duplicadas
    check = await db.execute(
        select(NodeJoinRequest).where(
            NodeJoinRequest.node_id == node_id,
            NodeJoinRequest.user_id == current_user.id,
            NodeJoinRequest.status == "pending",
        )
    )
    if check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Ya tienes una solicitud pendiente")

    req = NodeJoinRequest(node_id=node_id, user_id=current_user.id)
    db.add(req)
    await db.commit()
    return {"detail": "Solicitud enviada"}


@router.get("/{node_id}/requests", response_model=list[JoinRequestOut])
async def list_join_requests(
    node_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = await _get_user_node(db, current_user.id)
    if not membership or membership.node_id != node_id or membership.role != "admin":
        raise HTTPException(status_code=403, detail="Solo el admin puede ver las solicitudes")

    result = await db.execute(
        select(NodeJoinRequest)
        .where(NodeJoinRequest.node_id == node_id, NodeJoinRequest.status == "pending")
        .options(selectinload(NodeJoinRequest.user))
    )
    requests = result.scalars().all()
    return [
        JoinRequestOut(
            id=r.id,
            user_id=r.user_id,
            username=r.user.username,
            status=r.status,
            created_at=r.created_at,
        )
        for r in requests
    ]


@router.post("/{node_id}/requests/{request_id}/accept")
async def accept_request(
    node_id: int,
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = await _get_user_node(db, current_user.id)
    if not membership or membership.node_id != node_id or membership.role != "admin":
        raise HTTPException(status_code=403, detail="Solo el admin puede aceptar")

    result = await db.execute(
        select(NodeJoinRequest).where(
            NodeJoinRequest.id == request_id,
            NodeJoinRequest.node_id == node_id,
            NodeJoinRequest.status == "pending",
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    # Comprobar que el usuario no se haya unido a otro nodo mientras tanto
    other = await _get_user_node(db, req.user_id)
    if other:
        req.status = "rejected"
        await db.commit()
        raise HTTPException(status_code=400, detail="El usuario ya pertenece a otro nodo")

    req.status = "accepted"
    member = NodeMember(node_id=node_id, user_id=req.user_id, role="member")
    node_result = await db.execute(select(Node).where(Node.id == node_id))
    node = node_result.scalar_one()
    node.member_count += 1
    db.add(member)
    await db.commit()
    return {"detail": "Solicitud aceptada"}


@router.post("/{node_id}/requests/{request_id}/reject")
async def reject_request(
    node_id: int,
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = await _get_user_node(db, current_user.id)
    if not membership or membership.node_id != node_id or membership.role != "admin":
        raise HTTPException(status_code=403, detail="Solo el admin puede rechazar")

    result = await db.execute(
        select(NodeJoinRequest).where(
            NodeJoinRequest.id == request_id,
            NodeJoinRequest.node_id == node_id,
            NodeJoinRequest.status == "pending",
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    req.status = "rejected"
    await db.commit()
    return {"detail": "Solicitud rechazada"}


@router.post("/leave")
async def leave_node(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = await _get_user_node(db, current_user.id)
    if not membership:
        raise HTTPException(status_code=404, detail="No perteneces a ningún nodo")

    if membership.role == "admin":
        # Contar otros miembros
        count_result = await db.execute(
            select(func.count()).select_from(NodeMember).where(NodeMember.node_id == membership.node_id)
        )
        total = count_result.scalar_one()
        if total > 1:
            raise HTTPException(
                status_code=400,
                detail="Eres el admin. Transfiere el liderazgo antes de salir o elimina el nodo.",
            )

    node = membership.node
    node.member_count = max(0, node.member_count - 1)
    await db.delete(membership)
    await db.commit()
    return {"detail": "Has salido del nodo"}


@router.post("/{node_id}/transfer")
async def transfer_leadership(
    node_id: int,
    payload: TransferLeadership,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = await _get_user_node(db, current_user.id)
    if not membership or membership.node_id != node_id or membership.role != "admin":
        raise HTTPException(status_code=403, detail="Solo el admin puede transferir el liderazgo")

    result = await db.execute(
        select(NodeMember).where(
            NodeMember.node_id == node_id,
            NodeMember.user_id == payload.new_admin_user_id,
        )
    )
    new_admin = result.scalar_one_or_none()
    if not new_admin:
        raise HTTPException(status_code=404, detail="El usuario no es miembro del nodo")

    membership.role = "member"
    new_admin.role = "admin"
    await db.commit()
    return {"detail": "Liderazgo transferido"}


@router.delete("/{node_id}/members/{user_id}")
async def kick_member(
    node_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = await _get_user_node(db, current_user.id)
    if not membership or membership.node_id != node_id or membership.role != "admin":
        raise HTTPException(status_code=403, detail="Solo el admin puede expulsar miembros")

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes expulsarte a ti mismo")

    result = await db.execute(
        select(NodeMember).where(
            NodeMember.node_id == node_id,
            NodeMember.user_id == user_id,
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Miembro no encontrado")

    node = membership.node
    node.member_count = max(0, node.member_count - 1)
    await db.delete(target)
    await db.commit()
    return {"detail": "Miembro expulsado"}


# ========== Subida de logo ==========

from pathlib import Path
from fastapi import File, UploadFile
from fastapi.responses import FileResponse
import uuid
import shutil

UPLOAD_DIR = Path("uploads/nodes")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_SIZE = 1 * 1024 * 1024  # 1 MB
ALLOWED_CONTENT_TYPES = {"image/png"}


@router.post("/{node_id}/logo")
async def upload_logo(
    node_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Solo el admin del nodo puede subir logo
    membership = await _get_user_node(db, current_user.id)
    if not membership or membership.node_id != node_id or membership.role != "admin":
        raise HTTPException(status_code=403, detail="Solo el admin puede subir el logo")

    # Validaciones
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Solo se permiten imágenes PNG")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="El archivo no puede superar 1 MB")

    # Guardar archivo
    node_dir = UPLOAD_DIR / str(node_id)
    node_dir.mkdir(parents=True, exist_ok=True)
    filename = "logo.png"
    filepath = node_dir / filename

    with open(filepath, "wb") as f:
        f.write(content)

    # Actualizar URL en la base de datos
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one()
    node.logo_url = f"/uploads/nodes/{node_id}/logo.png"
    await db.commit()

    return {"logo_url": node.logo_url, "detail": "Logo actualizado"}


@router.get("/uploads/nodes/{node_id}/logo.png")
async def get_logo(node_id: int):
    """Sirve el logo del nodo (público)."""
    filepath = UPLOAD_DIR / str(node_id) / "logo.png"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Logo no encontrado")
    return FileResponse(filepath, media_type="image/png")


@router.delete("/{node_id}")
async def delete_node(
    node_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina el nodo completo (solo admin)."""
    membership = await _get_user_node(db, current_user.id)
    if not membership or membership.node_id != node_id or membership.role != "admin":
        raise HTTPException(status_code=403, detail="Solo el admin puede eliminar el nodo")

    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Nodo no encontrado")

    await db.delete(node)
    await db.commit()
    return {"detail": "Nodo eliminado"}
