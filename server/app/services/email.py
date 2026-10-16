"""Envío de emails con Resend."""
import resend
from app.core.config import settings

def send_password_reset_email(to_email: str, token: str) -> None:
    if not settings.RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY no configurada")

    resend.api_key = settings.RESEND_API_KEY
    # Enlace genérico: el cliente (GUI/CLI/APK) usará el token con la API
    # Si más adelante hay web: https://ecoclock.org/reset-password?token=...
    reset_hint = (
        f"Usa este token en la app o API (válido {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} min):\n\n"
        f"{token}\n\n"
        "Endpoint: POST /auth/reset-password\n"
        'Body: {"token": "<token>", "new_password": "<nueva>"}'
    )
    resend.Emails.send({
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": "Eco'clock — restablecer contraseña",
        "text": (
            "Has solicitado restablecer la contraseña de Eco'clock.\n\n"
            f"{reset_hint}\n\n"
            "Si no fuiste tú, ignora este correo."
        ),
    })
