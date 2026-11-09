"""Envío de emails con Resend."""
import base64
from pathlib import Path

import resend
from app.core.config import settings


_PASSWORD_RESET_EMAIL = {
    "es": {
        "subject": "Eco'clock — restablecer contraseña",
        "body": (
            "Has solicitado restablecer la contraseña de Eco'clock.\n\n"
            "Usa este token en la app o API (válido {minutes} min):\n\n"
            "{token}\n\n"
            "Endpoint: POST /auth/reset-password\n"
            'Body: {{"token": "<token>", "new_password": "<nueva>"}}\n\n'
            "Si no fuiste tú, ignora este correo."
        ),
    },
    "en": {
        "subject": "Eco'clock — reset password",
        "body": (
            "You requested a password reset for Eco'clock.\n\n"
            "Use this token in the app or API (valid {minutes} min):\n\n"
            "{token}\n\n"
            "Endpoint: POST /auth/reset-password\n"
            'Body: {{"token": "<token>", "new_password": "<new>"}}\n\n'
            "If this wasn't you, ignore this email."
        ),
    },
    "ca": {
        "subject": "Eco'clock — restablir contrasenya",
        "body": (
            "Has sol·licitat restablir la contrasenya d'Eco'clock.\n\n"
            "Usa aquest token a l'app o API (vàlid {minutes} min):\n\n"
            "{token}\n\n"
            "Endpoint: POST /auth/reset-password\n"
            'Body: {{"token": "<token>", "new_password": "<nova>"}}\n\n'
            "Si no has estat tu, ignora aquest correu."
        ),
    },
    "ja": {
        "subject": "Eco'clock — パスワード再設定",
        "body": (
            "Eco'clock のパスワード再設定がリクエストされました。\n\n"
            "アプリまたは API でこのトークンを使ってください（有効期限 {minutes} 分）:\n\n"
            "{token}\n\n"
            "Endpoint: POST /auth/reset-password\n"
            'Body: {{"token": "<token>", "new_password": "<新しいパスワード>"}}\n\n'
            "心当たりがない場合はこのメールを無視してください。"
        ),
    },
    "ar": {
        "subject": "Eco'clock — إعادة تعيين كلمة المرور",
        "body": (
            "تم طلب إعادة تعيين كلمة مرور Eco'clock.\n\n"
            "استخدم هذا الرمز في التطبيق أو واجهة API (صالح لمدة {minutes} دقيقة):\n\n"
            "{token}\n\n"
            "Endpoint: POST /auth/reset-password\n"
            'Body: {{"token": "<token>", "new_password": "<كلمة مرور جديدة>"}}\n\n'
            "إذا لم تطلب ذلك، تجاهل هذا البريد."
        ),
    },
    "fr": {
        "subject": "Eco'clock — réinitialiser le mot de passe",
        "body": (
            "Vous avez demandé la réinitialisation du mot de passe Eco'clock.\n\n"
            "Utilisez ce jeton dans l'app ou l'API (valide {minutes} min):\n\n"
            "{token}\n\n"
            "Endpoint: POST /auth/reset-password\n"
            'Body: {{"token": "<token>", "new_password": "<nouveau>"}}\n\n'
            "Si ce n'était pas vous, ignorez cet e-mail."
        ),
    },
    "de": {
        "subject": "Eco'clock — Passwort zurücksetzen",
        "body": (
            "Du hast das Zurücksetzen des Eco'clock-Passworts angefordert.\n\n"
            "Nutze dieses Token in der App oder API (gültig {minutes} Min.):\n\n"
            "{token}\n\n"
            "Endpoint: POST /auth/reset-password\n"
            'Body: {{"token": "<token>", "new_password": "<neu>"}}\n\n'
            "Falls du das nicht warst, ignoriere diese E-Mail."
        ),
    },
    "pt": {
        "subject": "Eco'clock — redefinir palavra-passe",
        "body": (
            "Pediu a redefinição da palavra-passe do Eco'clock.\n\n"
            "Use este token na app ou API (válido {minutes} min):\n\n"
            "{token}\n\n"
            "Endpoint: POST /auth/reset-password\n"
            'Body: {{"token": "<token>", "new_password": "<nova>"}}\n\n'
            "Se não foi você, ignore este e-mail."
        ),
    },
    "it": {
        "subject": "Eco'clock — reimposta password",
        "body": (
            "Hai richiesto il reset della password di Eco'clock.\n\n"
            "Usa questo token nell'app o API (valido {minutes} min):\n\n"
            "{token}\n\n"
            "Endpoint: POST /auth/reset-password\n"
            'Body: {{"token": "<token>", "new_password": "<nuova>"}}\n\n'
            "Se non sei stato tu, ignora questa email."
        ),
    },
    "zh": {
        "subject": "Eco'clock — 重置密码",
        "body": (
            "您请求重置 Eco'clock 密码。\n\n"
            "请在应用或 API 中使用此令牌（有效期 {minutes} 分钟）:\n\n"
            "{token}\n\n"
            "Endpoint: POST /auth/reset-password\n"
            'Body: {{"token": "<token>", "new_password": "<新密码>"}}\n\n'
            "如非本人操作，请忽略此邮件。"
        ),
    },
    "eu": {
        "subject": "Eco'clock — Pasahitza berrezarri",
        "body": (
            "Eco'clock-erako pasahitza berrezartzea eskatu duzu.\n\n"
            "Erabili token hau aplikazioan edo APIan (baliozko {minutes} min):\n\n"
            "{token}\n\n"
            "Endpoint: POST /auth/reset-password\n"
            'Body: {{"token": "<token>", "new_password": "<berria>"}}\n\n'
            "Hau ez bazara zu, ezikusi mezu elektroniko hau."
        ),
    },
    "ru": {
        "subject": "Eco'clock — сбросить пароль",
        "body": (
            "Вы запросили сброс пароля для Eco'clock.\n\n"
            "Используйте этот токен в приложении или API (действительный {minutes} минуты):\n\n"
            "{token}\n\n"
            "Endpoint: POST /auth/reset-password\n"
            'Body: {{"token": "<token>", "new_password": "<новый>"}}\n\n'
            "Если это были не вы, проигнорируйте это письмо."
        ),
    },
}


def send_password_reset_email(
    to_email: str,
    token: str,
    lang: str | None = "es",
) -> None:
    if not settings.RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY no configurada")

    resend.api_key = settings.RESEND_API_KEY
    code = (lang or "es").lower()[:2]
    t = _PASSWORD_RESET_EMAIL.get(code) or _PASSWORD_RESET_EMAIL["es"]
    minutes = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    body = t["body"].format(token=token, minutes=minutes)

    resend.Emails.send({
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": t["subject"],
        "text": body,
    })

# ---------------------------------------------------------------------------
# Sobre de Navegante (multi-idioma)
# ---------------------------------------------------------------------------

_NAVIGATOR_EMAIL = {
    "es": {
        "subject": "✉️ Tu Sobre de Navegante – Navegantes del Hielo",
        "greeting": "Hola, {name}",
        "intro": "Has desbloqueado el Sobre de Navegante. Aquí tienes el modelo 3D del cuadrante y la misión.",
        "mission_title": "Tu misión",
        "step1": "Imprime el cuadrante (STL adjunto, sin soportes).",
        "step2": "Mide la altura de una montaña con el cuadrante y anota los cálculos.",
        "step3": "Envía foto de la montaña + cálculos a validacion@ecoclock.org (asunto: Navegantes del Hielo + tu usuario).",
        "edu_title": "Cuadrante vs sextante",
        "edu_body": "El cuadrante histórico usa un arco de 90° y una plomada; el sextante moderno usa doble reflexión y un arco de 60°, más preciso en el mar. Esta actividad recupera el instrumento clásico para aprender midiendo.",
        "footer": "Eco'clock Network – Navegantes del Hielo",
        "attachment_name": "Cuadrante-Navegantes-del-Hielo.zip",
    },
    "en": {
        "subject": "✉️ Your Navigator Envelope – Ice Navigators",
        "greeting": "Hello, {name}",
        "intro": "You unlocked the Navigator Envelope. Here is the 3D quadrant model and your mission.",
        "mission_title": "Your mission",
        "step1": "Print the quadrant (STL attached, no supports).",
        "step2": "Measure a mountain's height with the quadrant and write down the calculations.",
        "step3": "Send a photo of the mountain + calculations to validacion@ecoclock.org (subject: Ice Navigators + your username).",
        "edu_title": "Quadrant vs sextant",
        "edu_body": "The historical quadrant uses a 90° arc and a plumb line; the modern sextant uses double reflection and a 60° arc, more precise at sea. This activity brings back the classic instrument so you learn by measuring.",
        "footer": "Eco'clock Network – Ice Navigators",
        "attachment_name": "Quadrant-Ice-Navigators.zip",
    },
    "ja": {
        "subject": "✉️ ナビゲーターの封筒 – 氷のナビゲーター",
        "greeting": "こんにちは、{name} さん",
        "intro": "ナビゲーターの封筒を解除しました。四分儀の3Dモデルとミッションです。",
        "mission_title": "ミッション",
        "step1": "四分儀を印刷してください（添付STL、サポート不要）。",
        "step2": "四分儀で山の高さを測り、計算を記録してください。",
        "step3": "山の写真と計算を validacion@ecoclock.org に送ってください（件名: 氷のナビゲーター + ユーザー名）。",
        "edu_title": "四分儀と六分儀",
        "edu_body": "歴史的な四分儀は90°の弧とおもりを使い、現代の六分儀は二重反射と60°の弧で海上ではより精密です。この活動では古典的な道具で測りながら学びます。",
        "footer": "Eco'clock Network – 氷のナビゲーター",
        "attachment_name": "Quadrant-Ice-Navigators.zip",
    },
    "ca": {
        "subject": "✉️ El teu sobre de navegant – Navegants del Gel",
        "greeting": "Hola, {name}",
        "intro": "Has desbloquejat el Sobre de Navegant. Aquí tens el model 3D del quadrant i la missió.",
        "mission_title": "La teva missió",
        "step1": "Imprimeix el quadrant (STL adjunt, sense suports).",
        "step2": "Mesura l'alçada d'una muntanya amb el quadrant i anota els càlculs.",
        "step3": "Envia foto de la muntanya + càlculs a validacion@ecoclock.org (assumpte: Navegants del Gel + el teu usuari).",
        "edu_title": "Quadrant vs sextant",
        "edu_body": "El quadrant històric usa un arc de 90° i una plomada; el sextant modern usa doble reflexió i un arc de 60°, més precís al mar. Aquesta activitat recupera l'instrument clàssic per aprendre mesurant.",
        "footer": "Eco'clock Network – Navegants del Gel",
        "attachment_name": "Quadrant-Navegants-del-Gel.zip",
    },
    "zh": {
        "subject": "✉️ 您的領航員信封 —— 冰區領航員",
        "greeting": "你好， {name}",
        "intro": "你已解鎖「領航員信封」。這裡是3D象限模型以及你的任務。",
        "mission_title": "你的任務",
        "step1": "列印此象限零件（附帶STL文件，無需支撐）。",
        "step2": "用象限儀測量山的高度，並記錄下計算過程。",
        "step3": "請將山峰照片及計算結果寄至 validacion@ecoclock.org（郵件主旨：Ice Navigators + 您的使用者名稱）。",
        "edu_title": "象限儀與六分儀",
        "edu_body": "歷史上的象限儀使用90°弧線和鉛垂線；現代六分儀使用雙重反射和60°弧線。, 在海上能實現更精確的測量。這項活動重現了經典儀器，讓你透過測量來學習。",
        "footer": "在海上能夠實現更精確的測量。本次活動新增了經典儀器，讓您透過測量來學習。",
        "attachment_name": "Quadrant-Ice-Navigators.zip",
    },
    "ru": {
        "subject": "✉️ Ваш конверт навигатора — Ice Navigators",
        "greeting": "Привет, {name}",
        "intro": "Вы открыли конверт «Навигатор». Внутри — 3D-модель квадранта и ваше задание.",
        "mission_title": "Ваша миссия",
        "step1": "Распечатайте квадрант (файл STL прилагается, поддержки не требуются).",
        "step2": "Измерьте высоту горы с помощью квадранта и запишите вычисления.",
        "step3": "Отправьте фотографию горы и расчёты на адрес validacion@ecoclock.org (тема письма: Ice Navigators + ваше имя пользователя).",
        "edu_title": "Квадрант и секстант",
        "edu_body": "В историческом квадранте используются дуга в 90° и отвес; в современном секстанте — двойное отражение и дуга в 60°., более точен в море. Этот вид деятельности возвращает к жизни классический инструмент значит, вы учитесь, проводя измерения.",
        "footer": "Eco'clock Network — «Ледовые навигаторы»",
        "attachment_name": "Quadrant-Ice-Navigators.zip",
    },
    "pt": {
        "subject": "✉️ Seu Envelope de Navegador – Navegadores de Gelo",
        "greeting": "Olá, {name}",
        "intro": "Você desbloqueou o Envelope do Navegador. Aqui estão o modelo 3D do quadrante e a sua missão.",
        "mission_title": "Sua missão",
        "step1": "Imprima o quadrante (STL em anexo, sem suportes).",
        "step2": "Meça a altura de uma montanha com o quadrante e anote os cálculos.",
        "step3": "Envie uma foto da montanha + os cálculos para validacion@ecoclock.org (assunto: Ice Navigators + seu nome de usuário).",
        "edu_title": "Quadrante versus sextante",
        "edu_body": "O quadrante histórico utiliza um arco de 90° e um fio de prumo; o sextante moderno utiliza dupla reflexão e um arco de 60°., mais preciso no mar. Esta atividade resgata o instrumento clássico então você aprende medindo.",
        "footer": "Rede Eco'clock – Navegadores do Gelo",
        "attachment_name": "Quadrant-Ice-Navigators.zip",
    },
    "it": {
        "subject": "✉️ La busta del tuo browser – Ice Browsers",
        "greeting": "Ciao, {name}",
        "intro": "Hai sbloccato la Busta del Navigatore. Ecco il modello 3D del quadrante e la tua missione.",
        "mission_title": "La tua missione",
        "step1": "Stampa il quadrante (file STL allegato, senza supporti).",
        "step2": "Misura l'altezza di una montagna con il quadrante e annota i calcoli.",
        "step3": "Invia una foto della montagna insieme ai calcoli all'indirizzo validacion@ecoclock.org (oggetto: Ice Navigators + il tuo nome utente).",
        "edu_title": "Quadrante contro sestante",
        "edu_body": "Il quadrante storico utilizza un arco di 90° e un filo a piombo; il sestante moderno sfrutta la doppia riflessione e un arco di 60°, risultando più preciso in mare. Questa attività riporta in auge lo strumento classico quindi impari misurando.",
        "footer": "Eco'clock Network – Navigatori dei ghiacci",
        "attachment_name": "Quadrant-Ice-Navigators.zip",
    },
    "eu": {
        "subject": "✉️ Zure nabigatzaile-gutunazala – Izotz-nabigatzaileak",
        "greeting": "Kaixo, {name}",
        "intro": "Nabigatzailearen gutun-azala desblokeatu duzu. Hona hemen kuadrantearen 3D eredua eta zure misioa.",
        "mission_title": "Zure misioa",
        "step1": "Inprimatu kuadrantea (STL erantsita, euskarririk gabe).",
        "step2": "Neurtu mendi baten altuera kuadrantearen bidez, eta idatzi kalkuluak.",
        "step3": "Bidali mendiaren argazki bat eta kalkuluak validacion@ecoclock.org helbidera (gaia: Ice Navigators + zure erabiltzaile-izena).",
        "edu_title": "Kuadrantea eta sextantea",
        "edu_body": "Kuadrante historikoak 90°-ko arkua eta berun-haria erabiltzen ditu; sextante modernoak, berriz, isla bikoitza eta 60°-ko arkua erabiltzen ditu, itsasoan zehatzagoa dena., zehatzagoa itsasoan. Jarduera honek tresna klasikoa berreskuratzen du, neurketen bidez ikas dezazun.",
        "footer": "Eco'clock Network – Izotz-nabigatzaileak",
        "attachment_name": "Quadrant-Ice-Navigators.zip",
    },
    "fr": {
        "subject": "✉️ Votre enveloppe « Navigateur » – Ice Navigators",
        "greeting": "Bonjour, {name}",
        "intro": "Vous avez déverrouillé l’enveloppe « Navigateur ». Voici le modèle 3D du quadrant ainsi que votre mission.",
        "mission_title": "Votre mission",
        "step1": "Imprimez le quadrant (fichier STL joint, sans supports).",
        "step2": "Mesurez la hauteur d’une montagne à l’aide du quadrant et notez les calculs.",
        "step3": "Envoyez une photo de la montagne ainsi que les calculs à validacion@ecoclock.org (objet : Ice Navigators + votre nom d’utilisateur).",
        "edu_title": "Quadrant contre sextant",
        "edu_body": "Le quadrant historique utilise un arc de 90° et un fil à plomb ; le sextant moderne fait appel à une double réflexion et à un arc de 60°, ce qui le rend plus précis en mer. Cette activité remet au goût du jour l'instrument classique, vous apprenez donc en mesurant.",
        "footer": "Réseau Eco'clock – Navigateurs des glaces",
        "attachment_name": "Quadrant-Ice-Navigators.zip",
    },
    "de": {
        "subject": "✉️ Ihr Navigator-Umschlag – Ice Navigators",
        "greeting": "Hallo, {name}",
        "intro": "Du hast den Navigator-Umschlag freigeschaltet. Hier sind das 3D-Quadrantenmodell und deine Mission.",
        "mission_title": "Deine Mission",
        "step1": "Drucke den Quadranten (STL beigefügt, keine Stützstrukturen).",
        "step2": "Messen Sie die Höhe eines Berges mithilfe des Quadranten und notieren Sie die Berechnungen.",
        "step3": "Sende ein Foto des Berges sowie die Berechnungen an validacion@ecoclock.org (Betreff: Ice Navigators + dein Benutzername).",
        "edu_title": "Quadrant vs. Sextant",
        "edu_body": "Der historische Quadrant verwendet einen 90°-Bogen und ein Senkblei; der moderne Sextant nutzt eine doppelte Spiegelung sowie einen 60°-Bogen und ist auf See präziser. Diese Aktivität greift auf das klassische Instrument zurück, sodass Sie durch Messen lernen.",
        "footer": "Eco'clock-Netzwerk – Eis-Navigatoren",
        "attachment_name": "Quadrant-Ice-Navigators.zip",
    },
    "ar": {
        "subject": "✉️ مظروف الملاح الخاص بك – ملاحو الجليد (Ice Navigators)",
        "greeting": "{name} مرحبًا،",
        "intro": "لقد قمت بفتح ظرف الملاحة. إليك نموذج الربع ثلاثي الأبعاد ومهمتك.",
        "mission_title": "مهمتك",
        "step1": "اطبع الربع (ملف STL مرفق، لا يتطلب دعامات).",
        "step2": "قِس ارتفاع جبلٍ باستخدام الربع الدائري، ودوّن الحسابات.",
        "step3": "أرسل صورة للجبل + الحسابات إلى العنوان validacion@ecoclock.org (مع كتابة Ice Navigators + اسم المستخدم الخاص بك في خانة الموضوع).",
        "edu_title": "الربع الدائري مقابل السدس الدائري",
        "edu_body": "يستخدم الربع الدائري التاريخي قوساً بزاوية 90 درجة وخيط شاقول، بينما يستخدم السدس الحديث تقنية الانعكاس المزدوج وقوساً بزاوية 60 درجة، وهو أكثر دقة في الملاحة البحرية. يُعيد هذا النشاط استخدام الأداة الكلاسيكية، لتتعلم من خلال القياس.",
        "footer": "ملاحو الجليد - Eco'clock Network",
        "attachment_name": "Quadrant-Ice-Navigators.zip",
    },
}


def _build_navigator_email(name: str, lang: str) -> tuple[str, str, str]:
    """Devuelve (subject, html, attachment_filename)."""
    t = _NAVIGATOR_EMAIL.get(lang) or _NAVIGATOR_EMAIL["es"]
    subject = t["subject"]
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0D1B1E;font-family:system-ui,-apple-system,sans-serif;">
  <div style="max-width:560px;margin:24px auto;background:#132A2E;border-radius:16px;padding:28px;border:1px solid #5B9EA6;color:#E8F4F5;">
    <h1 style="color:#5B9EA6;font-size:1.35rem;margin:0 0 12px;">{t["greeting"].format(name=name)}</h1>
    <p style="line-height:1.55;opacity:0.95;">{t["intro"]}</p>
    <h2 style="color:#9CCB5F;font-size:1.1rem;margin-top:24px;">{t["mission_title"]}</h2>
    <ol style="line-height:1.65;padding-left:1.25rem;">
      <li>{t["step1"]}</li>
      <li>{t["step2"]}</li>
      <li>{t["step3"]}</li>
    </ol>
    <h2 style="color:#9CCB5F;font-size:1.1rem;margin-top:24px;">{t["edu_title"]}</h2>
    <p style="line-height:1.55;opacity:0.9;">{t["edu_body"]}</p>
    <p style="margin-top:28px;font-size:0.85rem;opacity:0.65;">{t["footer"]}</p>
  </div>
</body>
</html>"""
    return subject, html, t["attachment_name"]


def send_navigator_envelope_email(
    to_email: str,
    username: str | None = None,
    lang: str | None = "es",
) -> None:
    """Envía el Sobre de Navegante con el ZIP del cuadrante adjunto."""
    if not settings.RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY no configurada")
    resend.api_key = settings.RESEND_API_KEY
    name = username or "Navegante"
    code = (lang or "es").lower()[:2]

    zip_path = Path("/app/assets/navigator-quadrant.zip")
    if not zip_path.exists():
        raise FileNotFoundError(f"No se encuentra el ZIP del cuadrante: {zip_path}")
    zip_bytes = zip_path.read_bytes()
    zip_b64 = base64.b64encode(zip_bytes).decode("utf-8")

    subject, html, att_name = _build_navigator_email(name, code)
    resend.Emails.send({
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html,
        "attachments": [
            {
                "filename": att_name,
                "content": zip_b64,
            }
        ],
    })
