"""Ventana principal de Eco'clock (Fase 2).Usa QStackedWidget para alternar entre vista de login y vista de tarea.
La logica vive en client.gui.services; aqui solo conectamos senales."""

from __future__ import annotations

import sys

# Import perezoso: si PyQt6 no esta instalado, este modulo aun es
# importable; el error se lanza solo al ejecutar la GUI.
try:
	from PyQt6.QtCore import Qt
	from PyQt6.QtGui import QAction
	from PyQt6.QtWidgets import (
		QApplication,
		QLabel,
		QLineEdit,
		QMainWindow,
		QMessageBox,
		QPushButton,
		QStackedWidget,
		QTextEdit,
		QVBoxLayout,
		QWidget,
	)
except ImportError:  # pragma: no cover - solo en tiempo de ejecucion
	QApplication = None  # type: ignore[assignment]


def main(argv: list[str] | None = None) -> int:
	if QApplication is None:
		raise RuntimeError(
			"PyQt6 no esta instalado. Instala con: "
			"pip install -r client/requirements-gui.txt"
		)

	app = QApplication(argv if argv is not None else sys.argv)
	window = EcoClockWindow()
	window.show()
	return app.exec()

class EcoClockWindow(QMainWindow):
	"""Ventana principal con QStackedWidget: login <-> tarea."""

	PAGE_LOGIN = 0
	PAGE_TASK = 1

	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle("Eco'clock")
		self.resize(480, 320)
		self.setMinimumSize(320, 240)
		self._center_on_screen()

		# Estado de sesion (lo rellena el login).
		self._base_url: str = "http://127.0.0.1:8000"
		self._token: str | None = None
		self._current_task: dict | None = None

		# Stack de paginas.
		self.stack = QStackedWidget(self)
		self.login_page = self._build_login_page()
		self.task_page = self._build_task_page()
		self.stack.addWidget(self.login_page)  # index 0
		self.stack.addWidget(self.task_page)   # index 1
		self.setCentralWidget(self.stack)

		# Menu basico con logout y salida.
		self._build_menu()
		self.statusBar().showMessage("Listo")

	def _center_on_screen(self) -> None:
		screen = QApplication.primaryScreen().availableGeometry()
		self.move(
			screen.center().x() - self.width() // 2,
			screen.center().y() - self.height() // 2,
		)

	def _build_menu(self) -> None:
		quit_action = QAction("&Salir", self)
		quit_action.setShortcut("Ctrl+Q")
		quit_action.triggered.connect(self.close)
		logout_action = QAction("&Cerrar sesion", self)
		logout_action.setShortcut("Ctrl+L")
		logout_action.triggered.connect(self._logout)
		menu = self.menuBar().addMenu("&Archivo")
		menu.addAction(logout_action)
		menu.addSeparator()
		menu.addAction(quit_action)

	def _build_login_page(self) -> QWidget:
		page = QWidget(self)
		layout = QVBoxLayout(page)
		self.username_input = QLineEdit(page)
		self.username_input.setPlaceholderText("username")
		self.password_input = QLineEdit(page)
		self.password_input.setPlaceholderText("password")
		self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
		self.login_button = QPushButton("Entrar", page)
		self.login_button.clicked.connect(self._on_login_clicked)
		layout.addWidget(QLabel("Login", page))
		layout.addWidget(self.username_input)
		layout.addWidget(self.password_input)
		layout.addWidget(self.login_button)
		return page

	def _build_task_page(self) -> QWidget:
		page = QWidget(self)
		layout = QVBoxLayout(page)
		self.task_label = QLabel("(sin tarea)", page)
		self.task_output = QTextEdit(page)
		self.task_output.setPlaceholderText('Output JSON, p.ej. {"ndvi": 0.34}')
		self.submit_button = QPushButton("Enviar", page)
		self.submit_button.clicked.connect(self._on_submit_clicked)
		layout.addWidget(self.task_label)
		layout.addWidget(self.task_output)
		layout.addWidget(self.submit_button)
		return page

	def _on_login_clicked(self) -> None:
		from client.gui import services  # import perezoso
		username = self.username_input.text().strip()
		password = self.password_input.text()
		if not username or not password:
			QMessageBox.warning(self, "Login", "Username y password son obligatorios.")
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
		self.statusBar().showMessage(f"Sesion iniciada como {username}")
		self._fetch_next_task()

	def _fetch_next_task(self) -> None:
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
		self.task_label.setText(f"Tarea #{tid}: {name}")
		self.task_output.clear()
		self.stack.setCurrentIndex(self.PAGE_TASK)

	def _on_submit_clicked(self) -> None:
		if not self._token or not self._current_task:
			return
		from client.gui import services
		raw = self.task_output.toPlainText().strip()
		try:
			import json
			output = json.loads(raw) if raw else {}
		except json.JSONDecodeError as exc:
			QMessageBox.warning(self, "Enviar", f"Output no es JSON valido:\n{exc}")
			return
		task_id = self._current_task.get("id")
		try:
			services.submit_task(
				self._base_url, self._token, task_id, output, 0.0,
			)
		except Exception as exc:  # noqa: BLE001
			QMessageBox.critical(self, "Enviar", f"Fallo al enviar:\n{exc}")
			return
		self.statusBar().showMessage(f"Tarea {task_id} enviada")
		self._fetch_next_task()

	def _logout(self) -> None:
		self._token = None
		self._current_task = None
		self.username_input.clear()
		self.password_input.clear()
		self.stack.setCurrentIndex(self.PAGE_LOGIN)
		self.statusBar().showMessage("Sesion cerrada")
