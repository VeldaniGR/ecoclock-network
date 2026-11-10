"""i18n mínimo para la GUI PyQt6 — alineado con la APK (12 idiomas)."""
from __future__ import annotations

from typing import Any

SUPPORTED = (
    ("es", "Español"),
    ("en", "English"),
    ("ca", "Català"),
    ("eu", "Euskera"),
    ("ja", "日本語"),
    ("ar", "العربية"),
    ("fr", "Français"),
    ("de", "Deutsch"),
    ("pt", "Português"),
    ("it", "Italiano"),
    ("zh", "中文"),
    ("ru", "Русский"),
)

_STRINGS: dict[str, dict[str, str]] = {
    "es": {
        # Login / Register
        "login_subtitle": "Dona tiempo de cómputo. Verifica a dónde va cada gota.",
        "login_user": "Usuario",
        "login_password": "Contraseña",
        "login_enter": "Entrar",
        "login_forgot": "¿Olvidaste tu contraseña?",
        "login_signup": "Crear cuenta",
        "login_lang": "Idioma",
        "login_missing": "Usuario y contraseña son obligatorios.",
        "login_fail": "Fallo de login:\n{err}",
        "login_no_token": "Respuesta sin access_token.",
        "forgot_title": "Recuperar contraseña",
        "forgot_prompt": "Email de la cuenta:",
        "forgot_ok": "Si el email existe, recibirás instrucciones en breve.",
        "forgot_fail": "No se pudo solicitar el reset:\n{err}",
        "register_title": "Crear cuenta",
        "register_email": "Email",
        "register_user": "Usuario",
        "register_password": "Contraseña",
        "register_confirm": "Confirmar contraseña",
        "register_submit": "Registrarse",
        "register_back": "Ya tengo cuenta",
        "register_mismatch": "Las contraseñas no coinciden.",
        "register_ok": "Cuenta creada. Ya puedes iniciar sesión.",
        "register_fail": "Error al registrar:\n{err}",

        # Dashboard
        "dash_welcome": "Hola, {user}",
        "dash_session": "Sesión",
        "dash_total_credits": "Créditos totales",
        "dash_session_credits": "Créditos esta sesión",
        "dash_compute_time": "Tiempo de cómputo",
        "dash_current_task": "Tarea actual",
        "dash_no_task": "No hay tarea pendiente",
        "dash_get_task": "Pedir tarea",
        "dash_submit": "Enviar resultado",
        "dash_auto": "Modo automático",
        "dash_auto_on": "Auto activado",
        "dash_auto_off": "Auto desactivado",
        "dash_nodes": "Nodos Ciudadanos",
        "dash_credits_history": "Historial de créditos",
        "dash_logout": "Cerrar sesión",
        "dash_expedition": "Expedición actual",
        "dash_expedition_none": "No hay expedición activa",
        "dash_progress": "Progreso",

        # Nodos
        "nodes_title": "Nodos Ciudadanos",
        "nodes_back": "← Volver",
        "nodes_loading": "Cargando...",
        "nodes_admin": "Administrador",
        "nodes_member": "Miembro",
        "nodes_members": "Miembros",
        "nodes_invite": "Enlace de unión",
        "nodes_copy": "Copiar",
        "nodes_frame": "Marco del logo",
        "nodes_frame_none": "Ninguno",
        "nodes_frame_hint": "Completa expediciones para desbloquear marcos.",
        "nodes_change_logo": "Cambiar logo",
        "nodes_rename": "Renombrar nodo",
        "nodes_requests": "Solicitudes pendientes",
        "nodes_no_requests": "No hay solicitudes pendientes.",
        "nodes_accept": "Aceptar",
        "nodes_reject": "Rechazar",
        "nodes_delete": "Eliminar nodo",
        "nodes_leave": "Salir del nodo",
        "nodes_create": "Crear un nodo",
        "nodes_create_btn": "Crear nodo",
        "nodes_name_ph": "Nombre del nodo",
        "nodes_join_code": "Unirse con enlace de unión",
        "nodes_join_btn": "Unirse al nodo",
        "nodes_code_ph": "Ej: QY8RY5LD",
        "nodes_explore": "Explorar nodos públicos",
        "nodes_no_public": "No hay nodos públicos todavía.",
        "nodes_request_join": "Solicitar unirse",
        "nodes_transfer": "Transferir",
        "nodes_kick": "Expulsar",
        "nodes_intro": "Únete a un nodo o crea el tuyo para colaborar con otros ciudadanos.",

        # Frames
        "frame_autumn_fungi": "Otoño · Hongos",
        "frame_arctic_ice": "Ártico · Hielo",

        # Comunes
        "error": "Error",
        "ok": "Aceptar",
        "cancel": "Cancelar",
        "copied": "Copiado al portapapeles",
        "confirm_delete": "¿Seguro que quieres eliminar el nodo?",
        "confirm_leave": "¿Seguro que quieres salir del nodo?",
        "confirm_kick": "¿Expulsar a {user}?",
        "confirm_transfer": "¿Transferir el liderazgo a {user}?",
    },

    "en": {
        "login_subtitle": "Donate idle compute. Verify where every drop goes.",
        "login_user": "Username",
        "login_password": "Password",
        "login_enter": "Sign in",
        "login_forgot": "Forgot password?",
        "login_signup": "Create account",
        "login_lang": "Language",
        "login_missing": "Username and password are required.",
        "login_fail": "Login failed:\n{err}",
        "login_no_token": "Response without access_token.",
        "forgot_title": "Reset password",
        "forgot_prompt": "Account email:",
        "forgot_ok": "If the email exists, you will receive instructions shortly.",
        "forgot_fail": "Could not request reset:\n{err}",
        "register_title": "Create account",
        "register_email": "Email",
        "register_user": "Username",
        "register_password": "Password",
        "register_confirm": "Confirm password",
        "register_submit": "Sign up",
        "register_back": "I already have an account",
        "register_mismatch": "Passwords do not match.",
        "register_ok": "Account created. You can sign in now.",
        "register_fail": "Registration error:\n{err}",

        "dash_welcome": "Hello, {user}",
        "dash_session": "Session",
        "dash_total_credits": "Total credits",
        "dash_session_credits": "Session credits",
        "dash_compute_time": "Compute time",
        "dash_current_task": "Current task",
        "dash_no_task": "No pending task",
        "dash_get_task": "Get task",
        "dash_submit": "Submit result",
        "dash_auto": "Automatic mode",
        "dash_auto_on": "Auto on",
        "dash_auto_off": "Auto off",
        "dash_nodes": "Citizen Nodes",
        "dash_credits_history": "Credits history",
        "dash_logout": "Log out",
        "dash_expedition": "Current expedition",
        "dash_expedition_none": "No active expedition",
        "dash_progress": "Progress",

        "nodes_title": "Citizen Nodes",
        "nodes_back": "← Back",
        "nodes_loading": "Loading...",
        "nodes_admin": "Administrator",
        "nodes_member": "Member",
        "nodes_members": "Members",
        "nodes_invite": "Join link",
        "nodes_copy": "Copy",
        "nodes_frame": "Logo frame",
        "nodes_frame_none": "None",
        "nodes_frame_hint": "Complete expeditions to unlock frames.",
        "nodes_change_logo": "Change logo",
        "nodes_rename": "Rename node",
        "nodes_requests": "Pending requests",
        "nodes_no_requests": "No pending requests.",
        "nodes_accept": "Accept",
        "nodes_reject": "Reject",
        "nodes_delete": "Delete node",
        "nodes_leave": "Leave node",
        "nodes_create": "Create a node",
        "nodes_create_btn": "Create node",
        "nodes_name_ph": "Node name",
        "nodes_join_code": "Join with invite code",
        "nodes_join_btn": "Join node",
        "nodes_code_ph": "E.g.: QY8RY5LD",
        "nodes_explore": "Explore public nodes",
        "nodes_no_public": "No public nodes yet.",
        "nodes_request_join": "Request to join",
        "nodes_transfer": "Transfer",
        "nodes_kick": "Kick",
        "nodes_intro": "Join a node or create your own to collaborate with other citizens.",

        "frame_autumn_fungi": "Autumn · Fungi",
        "frame_arctic_ice": "Arctic · Ice",

        "error": "Error",
        "ok": "OK",
        "cancel": "Cancel",
        "copied": "Copied to clipboard",
        "confirm_delete": "Are you sure you want to delete the node?",
        "confirm_leave": "Are you sure you want to leave the node?",
        "confirm_kick": "Kick {user}?",
        "confirm_transfer": "Transfer leadership to {user}?",
    },
}

# Rellenamos el resto de idiomas con fallback a inglés (puedes ir completándolos después)
for lang in ("ca", "eu", "ja", "ar", "fr", "de", "pt", "it", "zh", "ru"):
    if lang not in _STRINGS:
        _STRINGS[lang] = dict(_STRINGS["en"])  # copia profunda básica

# Sobrescribimos solo las claves más importantes en los idiomas que ya tenías
_STRINGS["ca"].update({
    "login_subtitle": "Dona temps de còmput. Verifica on va cada gota.",
    "login_user": "Usuari",
    "login_password": "Contrasenya",
    "login_enter": "Entrar",
    "login_forgot": "Has oblidat la contrasenya?",
    "login_signup": "Crear compte",
    "login_lang": "Idioma",
    "frame_autumn_fungi": "Tardor · Fongs",
    "frame_arctic_ice": "Àrtic · Gel",
    "nodes_title": "Nodes Ciutadans",
    "dash_nodes": "Nodes Ciutadans",
})

_STRINGS["eu"].update({
    "login_subtitle": "Eman konputazio-denbora. Egiaztatu non doan tanta bakoitza.",
    "login_user": "Erabiltzailea",
    "login_password": "Pasahitza",
    "login_enter": "Sartu",
    "login_lang": "Hizkuntza",
    "frame_autumn_fungi": "Udazkena · Onddoak",
    "frame_arctic_ice": "Artikoa · Izotza",
})

# (puedes seguir completando fr, de, pt, it, ja, zh, ru, ar igual que antes)

_current = "es"


def get_lang() -> str:
    return _current


def set_lang(code: str) -> None:
    global _current
    code = (code or "es").lower()[:2]
    known = {c for c, _ in SUPPORTED} | set(_STRINGS.keys())
    _current = code if code in known else "es"


def t(key: str, **kwargs: Any) -> str:
    """Traduce `key`; si falta, cae a es y luego a la propia key."""
    lang = _current
    bucket = _STRINGS.get(lang) or _STRINGS["es"]
    text = bucket.get(key) or _STRINGS["es"].get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text