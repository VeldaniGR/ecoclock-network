"""Buzón de contacto: webhook de Resend y bandeja del portal admin."""
import asyncio
import json
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_superadmin
from app.core.config import settings
from app.db.database import get_db
from app.db.models import ContactMessage, ContactThread, User, utcnow
from app.services import contact as contact_service

logger = logging.getLogger(__name__)

webhook_router = APIRouter(prefix="/contact", tags=["contact"])
admin_router = APIRouter(prefix="/admin/contact", tags=["admin"])


# ---------------------------------------------------------------- webhook

@webhook_router.post("/webhook", include_in_schema=False)
async def resend_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Recibe los eventos de Resend. Solo procesa email.received."""
    if not settings.RESEND_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook no configurado")

    payload = await request.body()  # cuerpo sin tocar: la firma se calcula sobre él
    if not contact_service.verify_svix_signature(
        payload, request.headers, settings.RESEND_WEBHOOK_SECRET
    ):
        raise HTTPException(status_code=401, detail="Firma no válida")

    try:
        event = json.loads(payload)
    except ValueError:
        raise HTTPException(status_code=400, detail="JSON no válido")

    if event.get("type") != "email.received":
        return {"ok": True, "ignored": True}

    email_id = (event.get("data") or {}).get("email_id")
    if not email_id:
        raise HTTPException(status_code=400, detail="Falta email_id")

    try:
        message, new_thread = await contact_service.ingest_received(db, email_id)
    except Exception:
        # Un error aquí hace que Resend reintente la entrega más tarde
        logger.exception("Fallo al procesar el correo recibido %s", email_id)
        raise HTTPException(status_code=502, detail="No se pudo procesar el correo")

    if message and new_thread:
        try:
            await asyncio.to_thread(contact_service.notify_new_thread)
        except Exception:
            logger.exception("Fallo al enviar el aviso de nuevo mensaje")

    return {"ok": True}


# ------------------------------------------------------------ bandeja admin

def _thread_out(t: ContactThread, count: int | None = None) -> dict:
    out = {
        "id": t.id,
        "subject": t.subject,
        "contact_email": t.contact_email,
        "contact_name": t.contact_name,
        "status": t.status,
        "is_read": t.is_read,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "last_message_at": t.last_message_at.isoformat() if t.last_message_at else None,
    }
    if count is not None:
        out["message_count"] = count
    return out


def _message_out(m: ContactMessage) -> dict:
    return {
        "id": m.id,
        "direction": m.direction,
        "from_addr": m.from_addr,
        "to_addr": m.to_addr,
        "subject": m.subject,
        "body_text": m.body_text,
        "auth_summary": m.auth_summary,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


async def _get_thread_or_404(db: AsyncSession, thread_id: int) -> ContactThread:
    thread = await db.get(ContactThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Hilo no encontrado")
    return thread


@admin_router.get("/threads")
async def list_threads(
    status: Literal["open", "closed", "all"] = "open",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    query = (
        select(ContactThread, func.count(ContactMessage.id))
        .outerjoin(ContactMessage, ContactMessage.thread_id == ContactThread.id)
        .group_by(ContactThread.id)
        .order_by(ContactThread.last_message_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status != "all":
        query = query.where(ContactThread.status == status)
    rows = (await db.execute(query)).all()

    unread = (
        await db.execute(
            select(func.count())
            .select_from(ContactThread)
            .where(ContactThread.status == "open")
            .where(ContactThread.is_read.is_(False))
        )
    ).scalar_one()

    return {"threads": [_thread_out(t, c) for t, c in rows], "unread": unread}


@admin_router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    thread = await _get_thread_or_404(db, thread_id)
    if not thread.is_read:
        thread.is_read = True
        await db.commit()
        await db.refresh(thread)

    messages = (
        await db.execute(
            select(ContactMessage)
            .where(ContactMessage.thread_id == thread_id)
            .order_by(ContactMessage.created_at.asc(), ContactMessage.id.asc())
        )
    ).scalars().all()
    return {"thread": _thread_out(thread), "messages": [_message_out(m) for m in messages]}


class ReplyIn(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


@admin_router.post("/threads/{thread_id}/reply")
async def reply_to_thread(
    thread_id: int,
    payload: ReplyIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_superadmin),
):
    thread = await _get_thread_or_404(db, thread_id)
    to_email = thread.contact_email
    base_subject = thread.subject
    admin_id = admin.id

    messages = (
        await db.execute(
            select(ContactMessage)
            .where(ContactMessage.thread_id == thread_id)
            .order_by(ContactMessage.created_at.asc(), ContactMessage.id.asc())
        )
    ).scalars().all()
    ids = [m.message_id for m in messages if m.message_id and m.direction in ("in", "out")]
    in_reply_to = ids[-1] if ids else None
    references = " ".join(ids[-10:]) or None
    subject = base_subject if base_subject.lower().startswith("re:") else f"Re: {base_subject}"

    try:
        email_id, message_id = await asyncio.to_thread(
            contact_service.send_reply,
            to_email=to_email,
            subject=subject,
            body=payload.body,
            in_reply_to=in_reply_to,
            references=references,
        )
    except Exception:
        logger.exception("Fallo al enviar la respuesta del hilo %s", thread_id)
        raise HTTPException(status_code=502, detail="No se pudo enviar la respuesta")

    db.add(
        ContactMessage(
            thread_id=thread_id,
            direction="out",
            resend_email_id=email_id,
            message_id=message_id,
            in_reply_to=in_reply_to,
            from_addr=settings.CONTACT_EMAIL,
            to_addr=to_email,
            subject=subject,
            body_text=payload.body,
            sent_by=admin_id,
        )
    )
    thread.last_message_at = utcnow()
    thread.is_read = True
    await db.commit()
    return {"ok": True}


class NoteIn(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


@admin_router.post("/threads/{thread_id}/note")
async def add_note(
    thread_id: int,
    payload: NoteIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_superadmin),
):
    await _get_thread_or_404(db, thread_id)
    db.add(
        ContactMessage(
            thread_id=thread_id,
            direction="note",
            from_addr=admin.username,
            body_text=payload.body,
            sent_by=admin.id,
        )
    )
    await db.commit()
    return {"ok": True}


class StatusIn(BaseModel):
    status: Literal["open", "closed"]


@admin_router.patch("/threads/{thread_id}")
async def set_thread_status(
    thread_id: int,
    payload: StatusIn,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    thread = await _get_thread_or_404(db, thread_id)
    thread.status = payload.status
    await db.commit()
    return {"ok": True, "status": payload.status}
