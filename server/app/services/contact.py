"""Buzón de contacto: recepción con Resend inbound y respuestas desde el portal."""
import asyncio
import base64
import hashlib
import hmac
import html as html_lib
import json
import logging
import re
import time
import urllib.request
from email.utils import parseaddr

import resend
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ContactMessage, ContactThread, utcnow

logger = logging.getLogger(__name__)

RESEND_API = "https://api.resend.com"
PANEL_URL = "https://api.ecoclock.org/admin"
MAX_BODY = 20000


# ---------------------------------------------------------------- firma Svix

def verify_svix_signature(payload: bytes, headers, secret: str) -> bool:
    """Verifica la firma de los webhooks de Resend (formato Svix)."""
    msg_id = headers.get("svix-id")
    timestamp = headers.get("svix-timestamp")
    signatures = headers.get("svix-signature")
    if not (msg_id and timestamp and signatures and secret):
        return False
    try:
        if abs(time.time() - int(timestamp)) > 300:  # ventana de 5 minutos
            return False
        raw_secret = secret.split("_", 1)[1] if secret.startswith("whsec_") else secret
        key = base64.b64decode(raw_secret)
    except ValueError:
        return False

    signed = f"{msg_id}.{timestamp}.".encode() + payload
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    for part in signatures.split():
        version, _, sig = part.partition(",")
        if version == "v1" and hmac.compare_digest(sig, expected):
            return True
    return False


# ------------------------------------------------------------ utilidades

def _resend_get(path: str) -> dict:
    """GET a la API de Resend con la librería estándar (no depende de la versión del SDK)."""
    req = urllib.request.Request(
        RESEND_API + path,
        headers={
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "User-Agent": "ecoclock-network/0.3",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _hdr(headers: dict, name: str) -> str:
    for key, value in (headers or {}).items():
        if key.lower() == name:
            return value if isinstance(value, str) else " ".join(value)
    return ""


_TAGS = re.compile(r"<(script|style)\b.*?</\1\s*>|<[^>]+>", re.S | re.I)


def html_to_text(html: str) -> str:
    text = re.sub(r"<br\s*/?>|</p\s*>|</div\s*>", "\n", html or "", flags=re.I)
    return html_lib.unescape(_TAGS.sub("", text)).strip()


_PREFIX = re.compile(r"^\s*((re|rv|fw|fwd|enc)\s*:\s*)+", re.I)


def normalize_subject(subject: str) -> str:
    return _PREFIX.sub("", subject or "").strip().lower()


def _own_addresses() -> set[str]:
    return {
        settings.CONTACT_EMAIL.lower(),
        parseaddr(settings.RESEND_FROM_EMAIL or "")[1].lower(),
    }


# --------------------------------------------------------------- recepción

async def ingest_received(db: AsyncSession, email_id: str) -> tuple[ContactMessage | None, bool]:
    """Guarda un correo recibido. Devuelve (mensaje, hilo_nuevo).

    Devuelve (None, False) si es un duplicado o se ignora (por ejemplo, un correo
    enviado por nosotros mismos, para evitar bucles).
    """
    already = (
        await db.execute(
            select(ContactMessage.id).where(ContactMessage.resend_email_id == email_id)
        )
    ).first()
    if already:
        return None, False

    data = await asyncio.to_thread(_resend_get, f"/emails/receiving/{email_id}")

    name, addr = parseaddr(data.get("from") or "")
    addr = addr.lower()
    if not addr or addr in _own_addresses():
        return None, False

    headers = data.get("headers") or {}
    subject = (data.get("subject") or "(sin asunto)")[:300]
    text = (data.get("text") or html_to_text(data.get("html") or ""))[:MAX_BODY]
    in_reply_to = _hdr(headers, "in-reply-to")
    references = _hdr(headers, "references")

    # 1) Hilo por cabeceras In-Reply-To / References
    thread = None
    refs = (in_reply_to + " " + references).split()
    if refs:
        row = (
            await db.execute(
                select(ContactMessage.thread_id)
                .where(ContactMessage.message_id.in_(refs))
                .limit(1)
            )
        ).first()
        if row:
            thread = await db.get(ContactThread, row[0])

    # 2) Alternativa: mismo remitente y mismo asunto (sin Re:/Fwd:)
    if thread is None:
        wanted = normalize_subject(subject)
        candidates = (
            await db.execute(
                select(ContactThread)
                .where(ContactThread.contact_email == addr)
                .order_by(ContactThread.last_message_at.desc())
                .limit(20)
            )
        ).scalars().all()
        thread = next((t for t in candidates if normalize_subject(t.subject) == wanted), None)

    new_thread = thread is None
    if new_thread:
        thread = ContactThread(subject=subject, contact_email=addr, contact_name=name[:200] or None)
        db.add(thread)
        await db.flush()

    thread.status = "open"
    thread.is_read = False
    thread.last_message_at = utcnow()

    auth = data.get("authentication") or {}
    auth_summary = (
        f"spf={auth.get('spf', '?')} dkim={auth.get('dkim', '?')} dmarc={auth.get('dmarc', '?')}"
        if auth else None
    )

    message = ContactMessage(
        thread_id=thread.id,
        direction="in",
        resend_email_id=email_id,
        message_id=(data.get("message_id") or "")[:500] or None,
        in_reply_to=in_reply_to[:500] or None,
        from_addr=addr,
        to_addr=", ".join(data.get("to") or [])[:320] or None,
        subject=subject,
        body_text=text,
        auth_summary=auth_summary,
    )
    db.add(message)
    try:
        await db.commit()
    except IntegrityError:  # el mismo correo llegó dos veces a la vez
        await db.rollback()
        return None, False
    return message, new_thread


def notify_new_thread() -> None:
    """Aviso mínimo al correo privado: sin contenido ni remitente."""
    if not settings.CONTACT_NOTIFY_EMAIL or not settings.RESEND_API_KEY:
        return
    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send({
        "from": settings.RESEND_FROM_EMAIL,
        "to": [settings.CONTACT_NOTIFY_EMAIL],
        "subject": "Nuevo mensaje en el buzón de Eco'clock",
        "text": f"Hay un mensaje nuevo en el buzón de contacto.\nRevísalo en el panel: {PANEL_URL}",
    })


# ------------------------------------------------------------------ envío

def send_reply(
    *,
    to_email: str,
    subject: str,
    body: str,
    in_reply_to: str | None,
    references: str | None,
) -> tuple[str, str | None]:
    """Envía una respuesta como contacto@ y devuelve (id_resend, message_id)."""
    if not settings.RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY no configurada")
    resend.api_key = settings.RESEND_API_KEY

    params = {
        "from": f"Eco'clock <{settings.CONTACT_EMAIL}>",
        "to": [to_email],
        "reply_to": settings.CONTACT_EMAIL,
        "subject": subject,
        "text": body,
    }
    headers = {}
    if in_reply_to:
        headers["In-Reply-To"] = in_reply_to
    if references:
        headers["References"] = references
    if headers:
        params["headers"] = headers

    sent = resend.Emails.send(params)
    email_id = sent["id"]

    message_id = None
    try:  # Resend expone el Message-ID del correo enviado; sirve para enlazar la respuesta del usuario
        message_id = _resend_get(f"/emails/{email_id}").get("message_id")
    except Exception:
        logger.warning("No se pudo obtener el message_id del correo %s", email_id)
    return email_id, message_id
