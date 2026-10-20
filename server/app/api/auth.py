"""Endpoints de autenticación: registro y login."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.models import PasswordResetToken
from app.schemas.user import ForgotPasswordRequest, ResetPasswordRequest
from app.services.email import send_password_reset_email
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.db.database import get_db
from app.db.models import User
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    username = payload.get("sub")
    result = await db.execute(select(User).where(User.username == username)); user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email ya registrado")
    existing = await db.execute(select(User).where(User.username == payload.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username ya en uso")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Solicita reset. Siempre responde igual (no revela si la cuenta existe)."""
    user = None
    identifier = (payload.email_or_username or (str(payload.email) if payload.email else None) or payload.username or "").strip()

    if payload.email:
        result = await db.execute(select(User).where(User.email == str(payload.email)))
        user = result.scalar_one_or_none()
    elif payload.username:
        result = await db.execute(select(User).where(User.username == payload.username))
        user = result.scalar_one_or_none()
    elif identifier:
        if "@" in identifier:
            result = await db.execute(select(User).where(User.email == identifier))
            user = result.scalar_one_or_none()
        if user is None:
            result = await db.execute(select(User).where(User.username == identifier))
            user = result.scalar_one_or_none()

    if user:
        raw = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=_hash_token(raw),
                expires_at=expires,
            )
        )
        await db.commit()
        try:
            send_password_reset_email(user.email, raw)
        except Exception:
            pass
    return {"detail": "Si la cuenta existe, recibirás instrucciones en breve."}



@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    token_hash = _hash_token(payload.token)
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
        )
    )
    row = result.scalar_one_or_none()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not row or row.expires_at < now:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")

    user_result = await db.execute(select(User).where(User.id == row.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")

    user.hashed_password = hash_password(payload.new_password)
    row.used_at = now
    await db.commit()
    return {"detail": "Contraseña actualizada correctamente."}
