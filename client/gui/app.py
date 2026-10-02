"""Ventana principal de Eco'clock (Fase 2+3 - UI redesign).

Estructura de páginas (QStackedWidget):
  0 - LoginPage:     login con logo, brand, inputs estilados, botón gradiente
  1 - DashboardPage: stats cards (sesión + total), tarea actual + progreso, formulario manual, toggle auto, sonar
  2 - RegisterPage:  registro de nuevos usuarios (usuario, email, contraseña)
  3 - CreditsPage:   historial de créditos (modal o página)

Incluye:
- Hoja animada (LeafWidget) en login y dashboard
- Sonar widget recoloreado
- Toggle switch recoloreado
- QSS global (theme.qss)
- Logo SVG propio
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Import perezoso: si PyQt6 no está instalado, este módulo aún es
# importable; el error se lanza solo al ejecutar la GUI.
try:
    from PyQt6.QtCore import Qt, QUrl, QTimer
    from PyQt6.QtGui import QAction, QDesktopServices, QPixmap
    from PyQt6.QtSvg import QSvgRenderer
    from PyQt6.QtWidgets import (
        QApplication,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QStackedWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # pragma: no cover
    QApplication = None  # type: ignore[assignment]
    Qt = QAction = QLabel = QLineEdit = None  # type: ignore[assignment]
    QMainWindow = QMessageBox = QPushButton = object  # type: ignore[assignment]
    QStackedWidget = QTextEdit = QVBoxLayout = QWidget = object  # type: ignore[assignment]
    QGridLayout = QHBoxLayout = QProgressBar = QFrame = QTimer = object  # type: ignore[assignment]
    QScrollArea = object  # type: ignore[assignment]
    QDesktopServices = QPixmap = QSvgRenderer = object  # type: ignore[assignment]


def main(argv: list[str] | None = None) -> int:
    if QApplication is None:
        raise RuntimeError(
            "PyQt6 no está instalado. Instala con: "
            "pip install -r client/requirements-gui.txt"
        )

    app = QApplication(argv if argv is not None else sys.argv)
    window = EcoClockWindow()
    window.show()
    return app.exec()


class EcoClockWindow(QMainWindow):
    """Ventana principal con QStackedWidget: login <-> dashboard <-> register <-> credits."""

    PAGE_LOGIN = 0
    PAGE_DASHBOARD = 1
    PAGE_REGISTER = 2
    PAGE_CREDITS = 3

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Eco'clock")
        self.resize(700, 500)  # Layout horizontal
        self.setMinimumSize(600, 450)
        self._center_on_screen()

        # Cargar QSS ANTES de crear widgets para que se aplique desde el inicio
        self._load_stylesheet()

        # Prioridad:
        # 1) export ECOCLOCK_BASE_URL=https://tu-ngrok...  (recomendado con APK)
        # 2) si no hay env → misma URL que usabas antes
        self._base_url: str = (
            os.environ.get("ECOCLOCK_BASE_URL") or "https://api.ecoclock.org"
        )
        self._token: str | None = None
        self._username: str | None = None  # Username loggeado para saludo personalizado
        self._current_task: dict | None = None
        self._auto_worker = None

        # Sesión: cronómetro y créditos ganados en esta sesión
        self._session_start_time: float | None = None
        self._session_compute_time: float = 0.0  # segundos totales de cómputo en sesión
        self._session_credits: int = 0  # créditos ganados en sesión
        self._session_timer = QTimer(self)
        self._session_timer.timeout.connect(self._update_session_stats)

        # Stack de páginas
        self.stack = QStackedWidget(self)
        self.stack.setObjectName("pageStack")

        self.login_page = self._build_login_page()
        self.dashboard_page = self._build_dashboard_page()
        self.register_page = self._build_register_page()
        self.credits_page = self._build_credits_page()

        self.stack.addWidget(self.login_page)      # index 0
        self.stack.addWidget(self.dashboard_page)  # index 1
        self.stack.addWidget(self.register_page)   # index 2
        self.stack.addWidget(self.credits_page)    # index 3

        self.setCentralWidget(self.stack)

        self._build_menu()
        self._build_status_bar()

    # ---------------------------------------------------------------------
    # Estilos y assets
    # ---------------------------------------------------------------------
    def _load_stylesheet(self) -> None:
        """Carga el QSS desde theme.qss en el mismo directorio."""
        qss_path = Path(__file__).with_name("theme.qss")
        if qss_path.exists():
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        else:
            print(f"[WARN] theme.qss no encontrado en {qss_path}", file=sys.stderr)

    def _load_logo_pixmap(self, size: int = 42) -> QPixmap:
        """Carga el logo SVG y lo renderiza a QPixmap del tamaño dado."""
        # Prioridad: logo local en client/gui/assets/ (adaptado para Qt)
        logo_paths = [
            Path(__file__).parent / "assets" / "logo.svg",
            Path(__file__).parent.parent.parent / "ecoclock_mobile" / "assets" / "logo.svg",
        ]
        for p in logo_paths:
            if p.exists():
                renderer = QSvgRenderer(str(p))
                pixmap = QPixmap(size, size)
                pixmap.fill(Qt.GlobalColor.transparent)
                from PyQt6.QtGui import QPainter
                from PyQt6.QtCore import QRectF
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                renderer.render(painter, QRectF(pixmap.rect()))
                painter.end()
                return pixmap
        # Fallback: pixmap vacío (se usará el fallback tipográfico)
        return QPixmap()

    # ---------------------------------------------------------------------
    # Construcción de páginas
    # ---------------------------------------------------------------------
    def _build_login_page(self) -> QWidget:
        """Página de login: logo, brand, subtitle, inputs, botón primario, links."""
        page = QWidget(self)
        page.setObjectName("loginPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 18, 34, 34)
        layout.setSpacing(0)

        # Hoja animada (esquina superior derecha)
        from client.gui.leaf_widget import LeafWidget
        self.leaf_login = LeafWidget(page)
        self.leaf_login.move(340, 56)  # posición estilo HTML: top:56px, right:26px
        self.leaf_login.start()

        # Brand row: logo + título
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)

        # Logo: intenta SVG, fallback a letra "e" con gradiente via QSS
        self.logo_label = QLabel(page)
        logo_pixmap = self._load_logo_pixmap(42)
        if not logo_pixmap.isNull():
            self.logo_label.setPixmap(logo_pixmap)
        else:
            self.logo_label.setText("e")
            self.logo_label.setProperty("class", "brandLogo")
            self.logo_label.setFixedSize(42, 42)
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = self.logo_label.font()
            font.setPointSize(20)
            font.setWeight(700)
            self.logo_label.setFont(font)
            self.logo_label.setStyleSheet("color: #fff8e6;")

        brand_row.addWidget(self.logo_label)

        # Título "Eco'clock" con span dorado
        title_widget = QWidget(page)
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        title_main = QLabel("Eco", title_widget)
        title_main.setProperty("class", "brandTitle")
        title_accent = QLabel("'clock", title_widget)
        title_accent.setProperty("class", "brandTitleAccent")

        title_layout.addWidget(title_main)
        title_layout.addWidget(title_accent)
        title_layout.addStretch(1)

        brand_row.addWidget(title_widget, stretch=1)
        layout.addLayout(brand_row)

        # Subtitle
        self.subtitle_label = QLabel(
            "Dona tiempo de cómputo. Verifica a dónde va cada gota.", page
        )
        self.subtitle_label.setProperty("class", "subtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setMaximumWidth(270)
        layout.addSpacing(14)
        layout.addWidget(self.subtitle_label)
        layout.addSpacing(22)

        # Inputs
        user_label = QLabel("Usuario", page)
        user_label.setProperty("class", "sectionLabel")
        layout.addWidget(user_label)

        self.username_input = QLineEdit(page)
        self.username_input.setPlaceholderText("tu usuario")
        self.username_input.setClearButtonEnabled(True)
        layout.addWidget(self.username_input)
        layout.addSpacing(10)

        pwd_label = QLabel("Contraseña", page)
        pwd_label.setProperty("class", "sectionLabel")
        layout.addWidget(pwd_label)

        self.password_input = QLineEdit(page)
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setClearButtonEnabled(True)
        layout.addWidget(self.password_input)
        layout.addSpacing(16)

        # Botón Entrar (primario)
        self.login_button = QPushButton("Entrar", page)
        self.login_button.setProperty("primary", True)
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.clicked.connect(self._on_login_clicked)
        layout.addWidget(self.login_button)
        layout.addSpacing(14)

        # Links inferiores
        links_row = QHBoxLayout()
        links_row.setContentsMargins(0, 0, 0, 0)

        self.forgot_btn = QPushButton("¿Olvidaste tu contraseña?", page)
        self.forgot_btn.setProperty("secondary", True)
        self.forgot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.forgot_btn.clicked.connect(self._on_forgot_password)

        self.signup_btn = QPushButton("Crear cuenta", page)
        self.signup_btn.setProperty("secondary", True)
        self.signup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.signup_btn.clicked.connect(lambda: self.stack.setCurrentIndex(self.PAGE_REGISTER))

        links_row.addWidget(self.forgot_btn)
        links_row.addStretch(1)
        links_row.addWidget(self.signup_btn)
        layout.addLayout(links_row)
        layout.addStretch(1)

        return page

    def _build_dashboard_page(self) -> QWidget:
        """Dashboard: layout horizontal con panel izquierdo (stats, tarea, formulario manual)
        y panel derecho (sonar + toggle)."""
        page = QWidget(self)
        page.setObjectName("dashboardPage")
        # Layout horizontal principal
        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ============================================================
        # PANEL IZQUIERDO: contenido principal (SIN scroll - cabe todo)
        # ============================================================
        left_widget = QWidget()
        left_widget.setObjectName("dashboardLeftPanel")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(34, 18, 34, 18)
        left_layout.setSpacing(0)

        # Hoja animada (esquina superior derecha del panel izquierdo)
        from client.gui.leaf_widget import LeafWidget
        self.leaf_dashboard = LeafWidget(left_widget)
        self.leaf_dashboard.move(300, 56)
        self.leaf_dashboard.start()

        # Brand row: logo + "Hola, {username}"
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)

        logo_dash = QLabel(left_widget)
        logo_pixmap = self._load_logo_pixmap(42)
        if not logo_pixmap.isNull():
            logo_dash.setPixmap(logo_pixmap)
        else:
            logo_dash.setText("e")
            logo_dash.setProperty("class", "brandLogo")
            logo_dash.setFixedSize(42, 42)
            logo_dash.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = logo_dash.font()
            font.setPointSize(20)
            font.setWeight(700)
            logo_dash.setFont(font)
            logo_dash.setStyleSheet("color: #fff8e6;")

        brand_row.addWidget(logo_dash)

        # Saludo personalizado (se actualiza en _on_login_clicked)
        self.dash_greeting = QLabel("Hola, <span>donante</span>", left_widget)
        self.dash_greeting.setProperty("class", "brandTitle")
        self.dash_greeting.setTextFormat(Qt.TextFormat.RichText)
        brand_row.addWidget(self.dash_greeting, stretch=1)
        left_layout.addLayout(brand_row)
        left_layout.addSpacing(18)

        # ---- Tarjetas de stats (grid 2x2): Sesión + Total ----
        cards_grid = QGridLayout()
        cards_grid.setSpacing(10)

        # Tarjeta 1: Horas esta sesión (cronómetro en vivo)
        self.card_session_hours = self._make_stat_card("0.0 h", "horas esta sesión")
        cards_grid.addWidget(self.card_session_hours, 0, 0)

        # Tarjeta 2: Créditos esta sesión (contador en vivo)
        self.card_session_credits = self._make_stat_card("0", "créditos esta sesión")
        cards_grid.addWidget(self.card_session_credits, 0, 1)

        # Tarjeta 3: Horas totales (desde API)
        self.card_total_hours = self._make_stat_card("—", "horas totales")
        cards_grid.addWidget(self.card_total_hours, 1, 0)

        # Tarjeta 4: Créditos totales (desde API)
        self.card_total_credits = self._make_stat_card("—", "créditos totales")
        cards_grid.addWidget(self.card_total_credits, 1, 1)

        left_layout.addLayout(cards_grid)
        left_layout.addSpacing(18)

        # ---- Tarea actual + barra de progreso ----
        self.dash_task_label = QLabel("Tarea actual", left_widget)
        self.dash_task_label.setProperty("class", "sectionLabel")
        left_layout.addWidget(self.dash_task_label)
        left_layout.addSpacing(6)

        self.dash_progress = QProgressBar(left_widget)
        self.dash_progress.setRange(0, 100)
        self.dash_progress.setValue(0)
        self.dash_progress.setTextVisible(False)
        self.dash_progress.setFixedHeight(10)
        left_layout.addWidget(self.dash_progress)
        left_layout.addSpacing(4)

        self.dash_progress_text = QLabel("Sin tarea activa", left_widget)
        self.dash_progress_text.setStyleSheet("color: #8a7556; font-size: 12px;")
        left_layout.addWidget(self.dash_progress_text)
        left_layout.addSpacing(18)

        # ---- Formulario de tarea manual (SIEMPRE VISIBLE) ----
        self.manual_task_widget = self._build_manual_task_widget(left_widget)
        left_layout.addWidget(self.manual_task_widget)
        left_layout.addStretch(1)

        main_layout.addWidget(left_widget, stretch=1)

        # ============================================================
        # PANEL DERECHO: Sonar widget + Toggle integrado
        # ============================================================
        right_widget = QWidget(page)
        right_widget.setObjectName("dashboardRightPanel")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 18, 18, 18)
        right_layout.setSpacing(12)

        # Header con toggle switch en la esquina superior derecha
        header_row = QHBoxLayout()
        header_row.addStretch(1)

        from client.gui.toggle_switch import ToggleSwitch
        self.auto_switch = ToggleSwitch("OFF     Automático     ON", right_widget)
        self.auto_switch.setMinimumWidth(180)
        self.auto_switch.toggled.connect(self._on_auto_toggled)
        header_row.addWidget(self.auto_switch)

        right_layout.addLayout(header_row)

        # Sonar widget (ocupa el resto del espacio)
        from client.gui.sonar_widget import SonarWidget
        self.sonar = SonarWidget(right_widget)
        self.sonar.setMinimumHeight(280)
        right_layout.addWidget(self.sonar, stretch=1)

        main_layout.addWidget(right_widget, stretch=1)

        return page

    def _build_manual_task_widget(self, parent: QWidget) -> QWidget:
        """Construye el widget del formulario de tarea manual (integrado en dashboard, siempre visible)."""
        widget = QWidget(parent)
        widget.setObjectName("manualTaskWidget")
        widget.setProperty("class", "manualTaskWidget")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Título sección
        label = QLabel("Tarea manual", widget)
        label.setProperty("class", "sectionLabel")
        layout.addWidget(label)
        layout.addSpacing(6)

        self.task_label = QLabel("(sin tarea)", widget)
        self.task_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #3b2d1d;")
        layout.addWidget(self.task_label)

        self.task_output = QTextEdit(widget)
        self.task_output.setPlaceholderText('Output JSON, p.ej. {"ndvi": 0.34}')
        self.task_output.setMinimumHeight(120)
        layout.addWidget(self.task_output, stretch=1)

        self.submit_button = QPushButton("Enviar resultado", widget)
        self.submit_button.setProperty("primary", True)
        self.submit_button.setProperty("accent", True)  # Para estilo dorado en QSS
        self.submit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.submit_button.clicked.connect(self._on_submit_clicked)
        layout.addWidget(self.submit_button)

        return widget

    def _make_stat_card(self, value: str, label: str) -> QWidget:
        """Crea una tarjeta de estadística estilo dashboard."""
        card = QWidget()
        card.setProperty("class", "statCard")
        card.setFixedHeight(80)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(2)

        val_label = QLabel(value)
        val_label.setProperty("class", "statValue")
        val_label.setObjectName("statValue")  # Para poder actualizarlo después
        layout.addWidget(val_label)

        lbl_label = QLabel(label)
        lbl_label.setProperty("class", "statLabel")
        layout.addWidget(lbl_label)

        return card

    def _build_register_page(self) -> QWidget:
        """Página de registro: usuario, email, contraseña, confirmar contraseña."""
        page = QWidget(self)
        page.setObjectName("registerPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 18, 34, 34)
        layout.setSpacing(0)

        # Hoja animada (esquina superior derecha)
        from client.gui.leaf_widget import LeafWidget
        self.leaf_register = LeafWidget(page)
        self.leaf_register.move(340, 56)
        self.leaf_register.start()

        # Brand row: logo + título
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)

        logo_reg = QLabel(page)
        logo_pixmap = self._load_logo_pixmap(42)
        if not logo_pixmap.isNull():
            logo_reg.setPixmap(logo_pixmap)
        else:
            logo_reg.setText("e")
            logo_reg.setProperty("class", "brandLogo")
            logo_reg.setFixedSize(42, 42)
            logo_reg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = logo_reg.font()
            font.setPointSize(20)
            font.setWeight(700)
            logo_reg.setFont(font)
            logo_reg.setStyleSheet("color: #fff8e6;")

        brand_row.addWidget(logo_reg)

        title_widget = QWidget(page)
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        title_main = QLabel("Eco", title_widget)
        title_main.setProperty("class", "brandTitle")
        title_accent = QLabel("'clock", title_widget)
        title_accent.setProperty("class", "brandTitleAccent")

        title_layout.addWidget(title_main)
        title_layout.addWidget(title_accent)
        title_layout.addStretch(1)

        brand_row.addWidget(title_widget, stretch=1)
        layout.addLayout(brand_row)

        # Subtitle
        subtitle = QLabel(
            "Crea tu cuenta para empezar a donar tiempo de cómputo.", page
        )
        subtitle.setProperty("class", "subtitle")
        subtitle.setWordWrap(True)
        subtitle.setMaximumWidth(270)
        layout.addSpacing(14)
        layout.addWidget(subtitle)
        layout.addSpacing(22)

        # Inputs
        user_label = QLabel("Usuario", page)
        user_label.setProperty("class", "sectionLabel")
        layout.addWidget(user_label)

        self.reg_username_input = QLineEdit(page)
        self.reg_username_input.setPlaceholderText("tu usuario")
        self.reg_username_input.setClearButtonEnabled(True)
        layout.addWidget(self.reg_username_input)
        layout.addSpacing(10)

        email_label = QLabel("Email", page)
        email_label.setProperty("class", "sectionLabel")
        layout.addWidget(email_label)

        self.reg_email_input = QLineEdit(page)
        self.reg_email_input.setPlaceholderText("tu@email.com")
        self.reg_email_input.setClearButtonEnabled(True)
        layout.addWidget(self.reg_email_input)
        layout.addSpacing(10)

        pwd_label = QLabel("Contraseña", page)
        pwd_label.setProperty("class", "sectionLabel")
        layout.addWidget(pwd_label)

        self.reg_password_input = QLineEdit(page)
        self.reg_password_input.setPlaceholderText("••••••••")
        self.reg_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_password_input.setClearButtonEnabled(True)
        layout.addWidget(self.reg_password_input)
        layout.addSpacing(10)

        pwd2_label = QLabel("Confirmar contraseña", page)
        pwd2_label.setProperty("class", "sectionLabel")
        layout.addWidget(pwd2_label)

        self.reg_password2_input = QLineEdit(page)
        self.reg_password2_input.setPlaceholderText("••••••••")
        self.reg_password2_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_password2_input.setClearButtonEnabled(True)
        layout.addWidget(self.reg_password2_input)
        layout.addSpacing(16)

        # Botón Registrarse (primario)
        self.register_button = QPushButton("Registrarse", page)
        self.register_button.setProperty("primary", True)
        self.register_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.register_button.clicked.connect(self._on_register_clicked)
        layout.addWidget(self.register_button)
        layout.addSpacing(14)

        # Link inferior
        links_row = QHBoxLayout()
        links_row.setContentsMargins(0, 0, 0, 0)

        self.login_link_btn = QPushButton("¿Ya tienes cuenta? Inicia sesión", page)
        self.login_link_btn.setProperty("secondary", True)
        self.login_link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_link_btn.clicked.connect(lambda: self.stack.setCurrentIndex(self.PAGE_LOGIN))

        links_row.addStretch(1)
        links_row.addWidget(self.login_link_btn)
        layout.addLayout(links_row)
        layout.addStretch(1)

        return page

    def _build_credits_page(self) -> QWidget:
        """Página de historial de créditos (modal o página)."""
        page = QWidget(self)
        page.setObjectName("creditsPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(34, 18, 34, 18)
        layout.setSpacing(12)

        # Header
        header_row = QHBoxLayout()
        back_btn = QPushButton("← Volver al dashboard", page)
        back_btn.setProperty("secondary", True)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(self.PAGE_DASHBOARD))
        header_row.addWidget(back_btn)
        header_row.addStretch(1)

        title = QLabel("Historial de créditos", page)
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #3b2d1d;")
        header_row.addWidget(title)
        header_row.addStretch(1)
        layout.addLayout(header_row)

        # Área scrollable para lista de créditos
        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.credits_container = QWidget()
        self.credits_layout = QVBoxLayout(self.credits_container)
        self.credits_layout.setContentsMargins(0, 0, 0, 0)
        self.credits_layout.setSpacing(8)
        self.credits_layout.addStretch(1)

        scroll.setWidget(self.credits_container)
        layout.addWidget(scroll, stretch=1)

        return page

    # ---------------------------------------------------------------------
    # Menú y Status Bar
    # ---------------------------------------------------------------------
    def _build_menu(self) -> None:
        self.menuBar().clear()

        # Menú Archivo
        menu = self.menuBar().addMenu("&Archivo")

        # Acción: Créditos
        credits_action = QAction("&Créditos / historial", self)
        credits_action.setShortcut("Ctrl+R")
        credits_action.triggered.connect(self._show_credits_page)
        menu.addAction(credits_action)

        menu.addSeparator()

        # Acción: Cerrar sesión
        logout_action = QAction("&Cerrar sesión", self)
        logout_action.setShortcut("Ctrl+L")
        logout_action.triggered.connect(self._logout)
        menu.addAction(logout_action)

        menu.addSeparator()

        # Acción: Salir
        quit_action = QAction("&Salir", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)

    def _build_status_bar(self) -> None:
        """Status bar con dot verde + texto."""
        self.statusBar().showMessage("Listo · API " + self._base_url)
        # El estilo se aplica via QSS (QStatusBar)
        # Para el dot verde, usamos un widget permanente
        from PyQt6.QtWidgets import QLabel, QHBoxLayout, QWidget

        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(18, 0, 18, 0)
        status_layout.setSpacing(8)

        self.status_dot = QLabel()
        self.status_dot.setFixedSize(8, 8)
        self.status_dot.setStyleSheet(
            "background-color: #6f9a4a; border-radius: 4px;"
        )
        status_layout.addWidget(self.status_dot)

        self.status_text = QLabel("Listo")
        self.status_text.setStyleSheet("color: #8a7556; font-size: 12px;")
        status_layout.addWidget(self.status_text)

        self.statusBar().addPermanentWidget(status_widget, 1)

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2,
        )

    # ---------------------------------------------------------------------
    # Slots / Lógica de negocio
    # ---------------------------------------------------------------------
    def _on_login_clicked(self) -> None:
        from client.gui import services

        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            QMessageBox.warning(self, "Login", "Usuario y contraseña son obligatorios.")
            return
        try:
            data = services.login(self._base_url, username, password)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Login", f"Fallo de login:\n{exc}")
            return
        self._token = data.get("access_token") if isinstance(data, dict) else None
        if not self._token:
            QMessageBox.critical(self, "Login", "Respuesta sin access_token.")
            return
        self._username = username
        # Actualizar saludo en dashboard
        self.dash_greeting.setText(f"Hola, <span>{username}</span>")
        self.status_text.setText(f"Sesión iniciada como {username}")
        self._fetch_dashboard_data()
        # Iniciar cronómetro de sesión
        self._session_start_time = time.time()
        self._session_compute_time = 0.0
        self._session_credits = 0
        self._session_timer.start(1000)  # Actualizar cada segundo
        self._update_session_stats()
        self.stack.setCurrentIndex(self.PAGE_DASHBOARD)

    def _on_register_clicked(self) -> None:
        from client.gui import services

        username = self.reg_username_input.text().strip()
        email = self.reg_email_input.text().strip()
        password = self.reg_password_input.text()
        password2 = self.reg_password2_input.text()

        if not username or not email or not password:
            QMessageBox.warning(self, "Registro", "Todos los campos son obligatorios.")
            return
        if password != password2:
            QMessageBox.warning(self, "Registro", "Las contraseñas no coinciden.")
            return
        if len(password) < 8:
            QMessageBox.warning(self, "Registro", "La contraseña debe tener al menos 8 caracteres.")
            return

        try:
            data = services.register(self._base_url, username, email, password)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Registro", f"Fallo de registro:\n{exc}")
            return

        QMessageBox.information(self, "Registro", "Cuenta creada correctamente. Ya puedes iniciar sesión.")
        # Limpiar formulario y volver a login
        self.reg_username_input.clear()
        self.reg_email_input.clear()
        self.reg_password_input.clear()
        self.reg_password2_input.clear()
        self.stack.setCurrentIndex(self.PAGE_LOGIN)

    def _fetch_dashboard_data(self) -> None:
        """Obtiene datos reales para el dashboard: créditos totales, tarea actual, etc."""
        if not self._token:
            return
        from client.gui import services

        try:
            # Créditos totales + recientes
            credits = services.me(self._base_url, self._token)  # usa /me/credits
            # Actualizar tarjetas de totales
            total_credits = credits.get("total", credits.get("totalCredits", 0))
            # Asumimos que la API devuelve también horas totales o lo calculamos
            total_hours = credits.get("totalHours", total_credits * 0.01)  # estimación
            self._update_total_stats_cards(total_hours, total_credits)
        except Exception:
            pass

        # Obtener tarea actual
        try:
            task = services.next_task(self._base_url, self._token)
            self._current_task = task
            self._update_dashboard_task(task)
        except Exception:
            pass

    def _update_total_stats_cards(self, total_hours: float, total_credits: int) -> None:
        """Actualiza las tarjetas de totales (desde API)."""
        # Formatear horas con 1 decimal
        self.card_total_hours.findChild(QLabel, "statValue").setText(f"{total_hours:.1f} h")
        # Formatear créditos con separador de miles
        self.card_total_credits.findChild(QLabel, "statValue").setText(f"{total_credits:,}".replace(",", "."))

    def _update_session_stats(self) -> None:
        """Actualiza las tarjetas de sesión (cronómetro en vivo)."""
        if self._session_start_time is None:
            return
        elapsed = time.time() - self._session_start_time
        # Horas de sesión (convertir segundos a horas con 1 decimal)
        session_hours = elapsed / 3600.0
        self.card_session_hours.findChild(QLabel, "statValue").setText(f"{session_hours:.1f} h")
        # Créditos de sesión
        self.card_session_credits.findChild(QLabel, "statValue").setText(str(self._session_credits))

    def _show_credits_page(self) -> None:
        if not self._token:
            QMessageBox.warning(self, "Créditos", "Inicia sesión primero.")
            return
        self._load_credits_history()
        self.stack.setCurrentIndex(self.PAGE_CREDITS)

    def _load_credits_history(self) -> None:
        """Carga el historial de créditos desde la API."""
        if not self._token:
            return

        # Limpiar container
        while self.credits_layout.count():
            item = self.credits_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        from client.gui import services
        import requests

        try:
            r = requests.get(
                self._base_url.rstrip("/") + "/me/credits",
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as exc:
            QMessageBox.critical(self, "Créditos", f"Error cargando créditos:\n{exc}")
            return

        total = data.get("total", data.get("totalCredits", "?"))
        # Total label
        total_label = QLabel(f"Total: {total}")
        total_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #3b2d1d; padding: 8px;")
        self.credits_layout.insertWidget(0, total_label)

        recent = data.get("recent") or []
        if not recent:
            empty = QLabel("Sin créditos recientes")
            empty.setStyleSheet("color: #8a7556; padding: 16px;")
            self.credits_layout.insertWidget(1, empty)
        else:
            for c in recent:
                if isinstance(c, dict):
                    amount = c.get("amount", "?")
                    task_id = c.get("task_id", "?")
                    granted = c.get("granted_at", "")
                    row = QLabel(f"· {amount} créditos  —  tarea #{task_id}  —  {granted}")
                    row.setStyleSheet("color: #3b2d1d; padding: 8px 0; font-family: monospace; font-size: 13px;")
                    self.credits_layout.insertWidget(self.credits_layout.count() - 1, row)

    def _fetch_next_task(self) -> None:
        """Obtiene la siguiente tarea y actualiza el formulario manual inline."""
        from client.gui import services

        if not self._token:
            return
        try:
            task = services.next_task(self._base_url, self._token)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Tarea", f"No se pudo obtener tarea:\n{exc}")
            return
        self._current_task = task
        tid = task.get("id", "?") if isinstance(task, dict) else "?"
        name = task.get("name", "?") if isinstance(task, dict) else "?"
        # Actualizar label en el formulario manual inline
        self.task_label.setText(f"Tarea #{tid}: {name}")
        self.task_output.clear()
        # También actualizar dashboard
        self._update_dashboard_task(task)

    def _update_dashboard_task(self, task: dict) -> None:
        """Actualiza la info de tarea actual en el dashboard."""
        tid = task.get("id", "?")
        name = task.get("name", "?")
        self.dash_task_label.setText(f"Tarea actual: #{tid} {name}")
        # TODO: calcular progreso real desde la API; por ahora mock
        self.dash_progress.setValue(64)
        self.dash_progress_text.setText("64 % completada")

    def _on_submit_clicked(self) -> None:
        if not self._token or not self._current_task:
            return
        from client.gui import services

        raw = self.task_output.toPlainText().strip()
        try:
            output = json.loads(raw) if raw else {}
        except json.JSONDecodeError as exc:
            QMessageBox.warning(self, "Enviar", f"Output no es JSON válido:\n{exc}")
            return
        task_id = self._current_task.get("id")
        try:
            services.submit_task(
                self._base_url, self._token, task_id, output, 0.0,
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Enviar", f"Fallo al enviar:\n{exc}")
            return
        self.status_text.setText(f"Tarea {task_id} enviada")
        # Actualizar stats de sesión (modo manual)
        self._session_credits += 1
        self._update_session_stats()
        self._fetch_next_task()

    def _on_auto_toggled(self, checked: bool) -> None:
        if checked:
            self._start_auto()
        else:
            self._stop_auto()

    def _start_auto(self) -> None:
        if not self._token:
            self.auto_switch.setChecked(False, animate=False)
            QMessageBox.warning(self, "Auto", "Inicia sesión primero.")
            return
        if self._auto_worker is not None and self._auto_worker.isRunning():
            return

        from client.gui.auto_worker import AutoWorker

        # Deshabilitar botón enviar (widget siempre visible)
        self.submit_button.setEnabled(False)

        self._auto_worker = AutoWorker(self._base_url, self._token, sleep_sec=1.0)
        self._auto_worker.task_started.connect(self._on_auto_task_started)
        self._auto_worker.task_finished.connect(self._on_auto_task_finished)
        self._auto_worker.error.connect(self._on_auto_error)
        self._auto_worker.stopped.connect(self._on_auto_stopped)

        self.sonar.start()
        self.sonar.set_status("Automático", "Buscando tarea…")
        self.status_text.setText("Modo automático activo…")
        self._auto_worker.start()

    def _stop_auto(self) -> None:
        if self._auto_worker is not None and self._auto_worker.isRunning():
            self._auto_worker.request_stop()
            self.status_text.setText("Parando automático…")
        else:
            self.sonar.stop()
            self.submit_button.setEnabled(True)

    def _on_auto_stopped(self, completed: int) -> None:
        self.submit_button.setEnabled(True)
        self.sonar.stop()
        self.status_text.setText(f"Auto detenido. Completadas: {completed}")
        if self.auto_switch.isChecked():
            self.auto_switch.setChecked(False, animate=True)
        # Cargar tarea para modo manual
        if self._token:
            self._fetch_next_task()

    def _on_auto_task_started(self, task: dict) -> None:
        tid = task.get("id", "?")
        name = task.get("name", "?")
        self.task_label.setText(f"[AUTO] Tarea #{tid}: {name}")
        self._current_task = task
        self.sonar.set_status("Procesando", f"#{tid} {name}")
        self._update_dashboard_task(task)

    def _on_auto_task_finished(self, result: dict, dt: float) -> None:
        tid = result.get("task_id", "?")
        self.status_text.setText(f"Auto: enviada #{tid} ({dt}s)")
        self.task_output.setPlainText(
            json.dumps(result.get("output") or {}, indent=2, ensure_ascii=False)
        )
        self.sonar.set_status("Enviada", f"task {tid} · {dt}s")
        # Actualizar stats de sesión
        self._session_compute_time += dt
        self._session_credits += 1  # Asumimos 1 crédito por tarea; ajustar según API
        self._update_session_stats()

    def _on_auto_error(self, msg: str) -> None:
        self.auto_switch.setChecked(False, animate=True)
        self.submit_button.setEnabled(True)
        self.sonar.stop()
        QMessageBox.critical(self, "Auto", f"Error en modo automático:\n{msg}")

    def _on_forgot_password(self) -> None:
        # TODO: implementar recuperación de contraseña
        QDesktopServices.openUrl(QUrl("https://ecoclock.org/password-reset"))

    def _on_signup(self) -> None:
        QDesktopServices.openUrl(QUrl("https://ecoclock.org/register"))

    def _logout(self) -> None:
        self._stop_auto()
        self._token = None
        self._username = None
        self._current_task = None
        self._session_timer.stop()
        self._session_start_time = None
        self.username_input.clear()
        self.password_input.clear()
        # Resetear saludo
        self.dash_greeting.setText("Hola, <span>donante</span>")
        # Resetear tarjetas de sesión
        self.card_session_hours.findChild(QLabel, "statValue").setText("0.0 h")
        self.card_session_credits.findChild(QLabel, "statValue").setText("0")
        self.stack.setCurrentIndex(self.PAGE_LOGIN)
        self.status_text.setText("Sesión cerrada")

    def closeEvent(self, event) -> None:
        self._stop_auto()
        if self._auto_worker is not None and self._auto_worker.isRunning():
            self._auto_worker.wait(3000)
        super().closeEvent(event)
