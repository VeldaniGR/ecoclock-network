"""Elegibilidad del Sobre de navegante (5 hexágonos / 25 tareas personales)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Credit, Expedition, NavigatorEnvelope, User, UserImpactHex

HEX_THRESHOLD = 5
TASK_THRESHOLD = 25
DEFAULT_TILE = "arctic"

# ---------------------------------------------------------------------------
# Mensajes multi-idioma del banner
# ---------------------------------------------------------------------------
MESSAGES = {
    "es": {
        "ready": "Tu sobre de navegante está listo",
        "sent": "Sobre enviado — completa la actividad exterior",
        "validated": "Actividad exterior validada — ¡Navegante del hielo!",
    },
    "en": {
        "ready": "Your navigator envelope is ready",
        "sent": "Envelope sent — complete the outdoor activity",
        "validated": "Outdoor activity validated — Ice Navigator!",
    },
    "ja": {
        "ready": "ナビゲーターの封筒の準備ができました",
        "sent": "封筒を送信しました — 屋外アクティビティを完了してください",
        "validated": "屋外アクティビティ認証済み — 氷のナビゲーター！",
    },
    "ca": {
        "ready": "El teu sobre de navegant està llest",
        "sent": "Sobre enviat — completa l'activitat exterior",
        "validated": "Activitat exterior validada — ¡Navegant del gel!",
    },
    "de": {
        "ready": "Dein Navigator-Umschlag ist bereit",
        "sent": "Umschlag gesendet — schließe die Outdoor-Aktivität ab",
        "validated": "Outdoor-Aktivität bestätigt — Eis-Navigator!",
    },
    "fr": {
        "ready": "Votre enveloppe de navigateur est prête",
        "sent": "Enveloppe envoyée — terminez l'activité en extérieur",
        "validated": "Activité en extérieur validée — Navigateur des glaces !",
    },
    "it": {
        "ready": "La tua busta del navigatore è pronta",
        "sent": "Busta inviata — completa l'attività all'aperto",
        "validated": "Attività all'aperto convalidata — Navigatore del ghiaccio!",
    },
    "pt": {
        "ready": "O teu envelope de navegador está pronto",
        "sent": "Envelope enviado — completa a atividade exterior",
        "validated": "Atividade exterior validada — Navegador do gelo!",
    },
    "ar": {
        "ready": "ظرف الملاح جاهز",
        "sent": "تم إرسال الظرف — أكمل النشاط الخارجي",
        "validated": "تم التحقق من النشاط الخارجي — ملاح الجليد!",
    },
    "zh": {
        "ready": "您的航海者信封已准备就绪",
        "sent": "信封已发送 — 请完成户外活动",
        "validated": "户外活动已验证 — 冰上航海者！",
    },
    "eu": {
        "ready": "Zure nabigatzaile-gutunazala prest dago",
        "sent": "Gutun-azala bidali da — osatu kanpoko jarduera",
        "validated": "Kanpoko jarduera balioztatua — Izotz-nabigatzailea!",
    },
    "ru": {
        "ready": "Ваш конверт штурмана готов",
        "sent": "Конверт отправлен — завершите активность на улице",
        "validated": "Активность на улице подтверждена — Ледяной штурман!",
    },
}


def _message_for(status: str, lang: str | None) -> str | None:
    if status not in ("ready", "sent", "validated"):
        return None
    code = (lang or "es").lower()[:2]
    if code not in MESSAGES:
        code = "es"
    return MESSAGES[code].get(status)


async def _active_arctic_expedition(db: AsyncSession) -> Expedition | None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = await db.execute(
        select(Expedition)
        .where(
            Expedition.is_active == True,  # noqa: E712
            Expedition.starts_at <= now,
            Expedition.ends_at >= now,
        )
        .order_by(Expedition.starts_at.desc())
    )
    rows = list(result.scalars().all())
    for e in rows:
        slug = (e.slug or "").lower()
        name = (e.name or "").lower()
        if "arctic" in slug or "winter" in slug or "hielo" in name or "artico" in name:
            return e
    return rows[0] if rows else None


async def count_hexes(
    db: AsyncSession, user_id: int, tile_slug: str = DEFAULT_TILE
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(UserImpactHex)
        .where(
            UserImpactHex.user_id == user_id,
            UserImpactHex.tile_slug == tile_slug,
        )
    )
    return int(result.scalar_one() or 0)


async def count_personal_tasks_in_window(
    db: AsyncSession,
    user_id: int,
    starts_at: datetime,
    ends_at: datetime,
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Credit)
        .where(
            Credit.user_id == user_id,
            Credit.granted_at >= starts_at,
            Credit.granted_at <= ends_at,
        )
    )
    return int(result.scalar_one() or 0)


async def get_envelope_state(db: AsyncSession, user_id: int) -> dict[str, Any]:
    exp = await _active_arctic_expedition(db)
    hex_count = await count_hexes(db, user_id, DEFAULT_TILE)

    if not exp:
        return {
            "status": "locked",
            "expedition_slug": None,
            "tile_slug": DEFAULT_TILE,
            "hex_count": hex_count,
            "hex_threshold": HEX_THRESHOLD,
            "personal_task_count": 0,
            "task_threshold": TASK_THRESHOLD,
            "message": None,
            "trigger": None,
        }

    task_count = await count_personal_tasks_in_window(
        db, user_id, exp.starts_at, exp.ends_at
    )

    result = await db.execute(
        select(NavigatorEnvelope).where(
            NavigatorEnvelope.user_id == user_id,
            NavigatorEnvelope.expedition_slug == exp.slug,
        )
    )
    row = result.scalar_one_or_none()

    if row and row.status in ("sent", "validated"):
        status = row.status
        trigger = row.trigger
    elif hex_count >= HEX_THRESHOLD or task_count >= TASK_THRESHOLD:
        trigger = "hexes" if hex_count >= HEX_THRESHOLD else "tasks"
        if row is None:
            row = NavigatorEnvelope(
                user_id=user_id,
                expedition_slug=exp.slug,
                tile_slug=DEFAULT_TILE,
                status="ready",
                trigger=trigger,
                hex_count_at_ready=hex_count,
                task_count_at_ready=task_count,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
        elif row.status not in ("sent", "validated"):
            row.status = "ready"
            row.trigger = trigger
            await db.commit()
        status = "ready"
        trigger = row.trigger
    else:
        status = "locked"
        trigger = None

    # Idioma preferido del usuario
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    lang = getattr(user, "preferred_language", None) if user else "es"
    message = _message_for(status, lang)

    return {
        "status": status,
        "expedition_slug": exp.slug,
        "tile_slug": DEFAULT_TILE,
        "hex_count": hex_count,
        "hex_threshold": HEX_THRESHOLD,
        "personal_task_count": task_count,
        "task_threshold": TASK_THRESHOLD,
        "message": message,
        "trigger": trigger,
    }


async def mark_envelope_sent(
    db: AsyncSession, user_id: int, expedition_slug: str
) -> dict[str, Any]:
    state = await get_envelope_state(db, user_id)
    if state.get("status") not in ("ready", "sent"):
        return state

    result = await db.execute(
        select(NavigatorEnvelope).where(
            NavigatorEnvelope.user_id == user_id,
            NavigatorEnvelope.expedition_slug == expedition_slug,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.status = "sent"
        row.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()

    # Enviar el email con el ZIP
    try:
        from app.services.email import send_navigator_envelope_email

        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.email:
            send_navigator_envelope_email(user.email, user.username)
    except Exception as e:
        print(f"[navigator_envelope] Error enviando email: {e}")

    return await get_envelope_state(db, user_id)

# Códigos de la loseta 10x10 (A1…J10) — el dorado ocupa el primero libre
_ALL_HEX_CODES = [
    f"{chr(ord('A') + r)}{c}"
    for r in range(10)
    for c in range(1, 11)
]


async def _pick_gold_hex_code(db: AsyncSession, user_id: int, tile_slug: str) -> str:
    """Elige un hex_code libre para el usuario en esa loseta (preferencia centro)."""
    result = await db.execute(
        select(UserImpactHex.hex_code).where(
            UserImpactHex.user_id == user_id,
            UserImpactHex.tile_slug == tile_slug,
        )
    )
    taken = {row[0].upper() for row in result.all()}
    # Preferir zona central (filas D–G, cols 4–7)
    preferred = [
        f"{chr(ord('A') + r)}{c}"
        for r in range(3, 7)
        for c in range(4, 8)
    ]
    for code in preferred + _ALL_HEX_CODES:
        if code.upper() not in taken:
            return code
    return "G5"  # fallback


async def validate_envelope(
    db: AsyncSession,
    user_id: int,
    expedition_slug: str | None = None,
    hex_code: str | None = None,
) -> dict[str, Any]:
    """
    Marca el sobre como validated y otorga un hexágono dorado.
    Idempotente: si ya está validated, solo asegura el hex gold.
    """
    state = await get_envelope_state(db, user_id)
    slug = expedition_slug or state.get("expedition_slug")
    if not slug:
        return state

    tile = state.get("tile_slug") or DEFAULT_TILE

    result = await db.execute(
        select(NavigatorEnvelope).where(
            NavigatorEnvelope.user_id == user_id,
            NavigatorEnvelope.expedition_slug == slug,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        # Crear fila si solo estaba "ready" en memoria
        row = NavigatorEnvelope(
            user_id=user_id,
            expedition_slug=slug,
            tile_slug=tile,
            status="validated",
            trigger=state.get("trigger"),
        )
        db.add(row)
    else:
        row.status = "validated"
        if row.validated_at is None:
            row.validated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # Hexágono dorado
    code = (hex_code or await _pick_gold_hex_code(db, user_id, tile)).upper()
    existing = await db.execute(
        select(UserImpactHex).where(
            UserImpactHex.user_id == user_id,
            UserImpactHex.tile_slug == tile,
            UserImpactHex.hex_code == code,
        )
    )
    hex_row = existing.scalar_one_or_none()
    if hex_row is None:
        db.add(
            UserImpactHex(
                user_id=user_id,
                tile_slug=tile,
                hex_code=code,
                color="gold",
                source="photo_validated",
                expedition_slug=slug,
                validated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
    else:
        # Si ya existía (p.ej. glacier), lo promocionamos a gold
        hex_row.color = "gold"
        hex_row.source = "photo_validated"
        hex_row.validated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if not hex_row.expedition_slug:
            hex_row.expedition_slug = slug

    await db.commit()
    return await get_envelope_state(db, user_id)
