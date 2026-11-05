"""Envío de emails con Resend."""
import base64
from pathlib import Path

import resend
from app.core.config import settings


def send_password_reset_email(to_email: str, token: str) -> None:
    if not settings.RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY no configurada")

    resend.api_key = settings.RESEND_API_KEY
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


def send_navigator_envelope_email(to_email: str, username: str | None = None) -> None:
    """Envía el Sobre de Navegante con el ZIP del cuadrante adjunto."""
    if not settings.RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY no configurada")

    resend.api_key = settings.RESEND_API_KEY
    name = username or "Navegante"

    # Ruta absoluta en el servidor
    zip_path = Path("/opt/ecoclock-network/server/assets/navigator-quadrant.zip")

    if not zip_path.exists():
        raise FileNotFoundError(f"No se encuentra el ZIP del cuadrante: {zip_path}")

    zip_bytes = zip_path.read_bytes()
    zip_b64 = base64.b64encode(zip_bytes).decode("utf-8")

    html = _build_navigator_email_html(name)

    resend.Emails.send({
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": "✉️ Tu Sobre de Navegante – Navegantes del Hielo",
        "html": html,
        "attachments": [
            {
                "filename": "Cuadrante-Navegantes-del-Hielo.zip",
                "content": zip_b64,
            }
        ],
    })


def _build_navigator_email_html(name: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sobre de Navegante</title>
</head>
<body style="margin:0; padding:0; background-color:#f0f7f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0f7f9; padding: 40px 16px;">
    <tr>
      <td align="center">
        <table width="100%" style="max-width:580px; background: linear-gradient(180deg, #ffffff 0%, #f7fcfd 100%); border-radius: 20px; overflow: hidden; box-shadow: 0 12px 40px rgba(91, 158, 166, 0.15);">

          <!-- Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #5B9EA6 0%, #3d7a82 100%); padding: 32px 32px 24px; text-align: center;">
              <h1 style="margin:0; color:#ffffff; font-size: 26px; font-weight: 700; letter-spacing: -0.5px;">
                ✉️ Sobre de Navegante
              </h1>
              <p style="margin: 8px 0 0; color: rgba(255,255,255,0.9); font-size: 15px;">
                Navegantes del Hielo
              </p>
            </td>
          </tr>

          <!-- Contenido -->
          <tr>
            <td style="padding: 36px 32px 24px;">
              <p style="margin:0 0 20px; font-size: 17px; color:#1a2b2e; line-height: 1.5;">
                ¡Hola <strong>{name}</strong>!
              </p>

              <p style="margin:0 0 24px; font-size: 16px; color:#334155; line-height: 1.6;">
                Has desbloqueado el <strong>Sobre de Navegante</strong>.
                Ahora toca demostrar que eres digno del título de
                <strong style="color:#5B9EA6;">Navegantes del Hielo</strong>.
              </p>

              <!-- Caja de misión -->
              <div style="background: rgba(91, 158, 166, 0.08); border-left: 4px solid #5B9EA6; border-radius: 12px; padding: 20px 22px; margin-bottom: 28px;">
                <p style="margin:0 0 12px; font-size: 15px; font-weight: 700; color:#1a2b2e;">
                  🧊 Tu misión
                </p>
                <ol style="margin:0; padding-left: 20px; color:#334155; font-size: 15px; line-height: 1.7;">
                  <li style="margin-bottom: 10px;">
                    Descarga el archivo ZIP adjunto e imprime el <strong>Cuadrante</strong> (predecesor del sextante).
                  </li>
                  <li style="margin-bottom: 10px;">
                    Móntalo y úsalo para medir la <strong>altura de una montaña real</strong>.
                  </li>
                  <li style="margin-bottom: 10px;">
                    Calcula la altura y explica brevemente el método que has usado.
                  </li>
                  <li>
                    Envíanos una foto de la montaña + tus cálculos (responde a este correo o súbela en la app).
                  </li>
                </ol>
              </div>

              <!-- Explicación educativa -->
              <div style="background: #f8fafc; border-radius: 12px; padding: 20px 22px; margin-bottom: 28px; border: 1px solid #e2e8f0;">
                <p style="margin:0 0 12px; font-size: 15px; font-weight: 700; color:#1a2b2e;">
                  📚 Cuadrante vs Sextante – lo que debes saber
                </p>
                <p style="margin:0 0 12px; font-size: 14px; color:#475569; line-height: 1.65;">
                  El <strong>cuadrante</strong> es el instrumento más antiguo de los dos. Es literalmente un cuarto de círculo (90°) con una escala graduada. Tradicionalmente se usaba con una plomada para medir la altura angular de un astro sobre el horizonte. Es más simple y robusto, pero menos preciso y más sensible a los movimientos.
                </p>
                <p style="margin:0 0 12px; font-size: 14px; color:#475569; line-height: 1.65;">
                  El <strong>sextante</strong> (siglo XVIII) supone un salto tecnológico:
                </p>
                <ul style="margin:0 0 12px; padding-left: 20px; color:#475569; font-size: 14px; line-height: 1.65;">
                  <li>Usa <strong>doble reflexión</strong> con espejos.</li>
                  <li>Su arco es de 60°, pero gracias a la doble reflexión puede medir ángulos de hasta 120°.</li>
                  <li>No necesita una plomada fija: el observador ve al mismo tiempo el horizonte y el astro reflejado.</li>
                </ul>
                <p style="margin:0; font-size: 14px; color:#475569; line-height: 1.65;">
                  En resumen: el cuadrante es el abuelo directo del sextante. Al construirlo y usarlo estás experimentando exactamente el principio físico y matemático que más tarde se perfeccionó en el sextante moderno.
                </p>
              </div>

              <p style="margin:0 0 8px; font-size: 15px; color:#334155; line-height: 1.6;">
                Cuando lo valides recibirás el <strong>hexágono dorado</strong> y el título oficial de
                <em>Navegantes del Hielo</em>.
              </p>

              <p style="margin: 28px 0 0; font-size: 15px; color:#5B9EA6; font-weight: 600;">
                ¡Buen viento y buena altura!
              </p>
              <p style="margin: 4px 0 0; font-size: 14px; color:#64748b;">
                — Equipo Eco'clock
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background: #f0f7f9; padding: 20px 32px; text-align: center; border-top: 1px solid #e2eef1;">
              <p style="margin:0; font-size: 12px; color:#94a3b8;">
                Eco'clock · Navegantes del Hielo · <a href="https://ecoclock.org" style="color:#5B9EA6; text-decoration:none;">ecoclock.org</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""
