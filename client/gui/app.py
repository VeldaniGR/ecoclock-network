"""Ventana principal de Eco'clock (Fase 2).

Usa QStackedWidget para alternar entre vista de login y vista de tarea.
Incluye modo automático (ToggleSwitch) y animación tipo sónar.
La lógica HTTP vive en client.gui.services; el cómputo en client.ndvi.
"""

from __future__ import annotations

import json
import os
import sys

# Import perezoso: si PyQt6 no está instalado, este módulo aún es
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
except ImportError:  # pragma: no cover
	QApplication = None  # type: ignore[assignment]
	Qt = QAction = QLabel = QLineEdit = None  # type: ignore[assignment]
	QMainWindow = QMessageBox = QPushButton = object  # type: ignore[assignment]
	QStackedWidget = QTextEdit = QVBoxLayout = QWidget = object  # type: ignore[assignment]


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
	"""Ventana principal con QStackedWidget: login <-> tarea."""

	PAGE_LOGIN = 0
	PAGE_TASK = 1

	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle("Eco'clock")
		self.resize(520, 520)
		self.setMinimumSize(360, 400)
		self._center_on_screen()

		# Prioridad:
		# 1) export ECOCLOCK_BASE_URL=https://tu-ngrok...  (recomendado con APK)
		# 2) si no hay env → misma URL que usabas antes
		self._base_url: str = (
			os.environ.get("ECOCLOCK_BASE_URL") or "https://api.ecoclock.org"
		)
		self._token: str | None = None
		self._current_task: dict | None = None
		self._auto_worker = None

		# Stack de páginas.
		self.stack = QStackedWidget(self)
		self.login_page = self._build_login_page()
		self.task_page = self._build_task_page()
		self.stack.addWidget(self.login_page)  # index 0
		self.stack.addWidget(self.task_page)   # index 1
		self.setCentralWidget(self.stack)

		self._build_menu()
		self.statusBar().showMessage(f"Listo · API {self._base_url}")


	def _center_on_screen(self) -> None:
		screen = QApplication.primaryScreen().availableGeometry()
		self.move(
			screen.center().x() - self.width() // 2,
			screen.center().y() - self.height() // 2,
		)

	def _build_menu(self) -> None:
		self.menuBar().clear()
		quit_action = QAction("&Salir", self)
		quit_action.setShortcut("Ctrl+Q")
		quit_action.triggered.connect(self.close)
		logout_action = QAction("&Cerrar sesión", self)
		logout_action.setShortcut("Ctrl+L")
		logout_action.triggered.connect(self._logout)
		menu = self.menuBar().addMenu("&Archivo")
		credits_action = QAction("&Créditos / historial", self)
		credits_action.triggered.connect(self._show_credits)
		menu.addAction(credits_action)
		menu.addSeparator()
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
		layout.addStretch(1)
		return page

	def _build_task_page(self) -> QWidget:
		from client.gui.sonar_widget import SonarWidget
		from client.gui.toggle_switch import ToggleSwitch

		page = QWidget(self)
		layout = QVBoxLayout(page)

		self.task_label = QLabel("(sin tarea)", page)
		self.task_output = QTextEdit(page)
		self.task_output.setPlaceholderText('Output JSON, p.ej. {"ndvi": 0.34}')
		self.submit_button = QPushButton("Enviar", page)
		self.submit_button.clicked.connect(self._on_submit_clicked)

		self.sonar = SonarWidget(page)
		self.auto_switch = ToggleSwitch("Activar", page)
		self.auto_switch.toggled.connect(self._on_auto_toggled)

		layout.addWidget(self.task_label)
		layout.addWidget(self.sonar, stretch=1)
		layout.addWidget(self.task_output)
		layout.addWidget(self.submit_button)
		layout.addWidget(self.auto_switch)
		return page

	def _on_login_clicked(self) -> None:
		from client.gui import services

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
		self.statusBar().showMessage(f"Sesión iniciada como {username}")
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
		self.statusBar().showMessage(f"Tarea {task_id} enviada")
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

		self.submit_button.setEnabled(False)
		self._auto_worker = AutoWorker(self._base_url, self._token, sleep_sec=1.0)
		self._auto_worker.task_started.connect(self._on_auto_task_started)
		self._auto_worker.task_finished.connect(self._on_auto_task_finished)
		self._auto_worker.error.connect(self._on_auto_error)
		self._auto_worker.stopped.connect(self._on_auto_stopped)

		self.sonar.start()
		self.sonar.set_status("Automático", "Buscando tarea…")
		self.statusBar().showMessage("Modo automático activo…")
		self._auto_worker.start()

	def _stop_auto(self) -> None:
		if self._auto_worker is not None and self._auto_worker.isRunning():
			self._auto_worker.request_stop()
			self.statusBar().showMessage("Parando automático…")
		else:
			self.sonar.stop()
			self.submit_button.setEnabled(True)

	def _on_auto_stopped(self, completed: int) -> None:
		self.submit_button.setEnabled(True)
		self.sonar.stop()
		self.statusBar().showMessage(f"Auto detenido. Completadas: {completed}")
		if self.auto_switch.isChecked():
			self.auto_switch.setChecked(False, animate=True)
		# Cargar una tarea nueva para modo manual
		if self._token:
			self._fetch_next_task()

	def _on_auto_task_started(self, task: dict) -> None:
		tid = task.get("id", "?")
		name = task.get("name", "?")
		self.task_label.setText(f"[AUTO] Tarea #{tid}: {name}")
		self._current_task = task
		self.sonar.set_status("Procesando", f"#{tid} {name}")

	def _on_auto_task_finished(self, result: dict, dt: float) -> None:
		tid = result.get("task_id", "?")
		self.statusBar().showMessage(f"Auto: enviada #{tid} ({dt}s)")
		self.task_output.setPlainText(
			json.dumps(result.get("output") or {}, indent=2, ensure_ascii=False)
		)
		self.sonar.set_status("Enviada", f"task {tid} · {dt}s")

	def _on_auto_error(self, msg: str) -> None:
		self.auto_switch.setChecked(False, animate=True)
		self.submit_button.setEnabled(True)
		self.sonar.stop()
		QMessageBox.critical(self, "Auto", f"Error en modo automático:\n{msg}")

	def _show_credits(self) -> None:
		if not self._token:
			QMessageBox.warning(self, "Créditos", "Inicia sesión primero.")
			return
		from client.gui import services
		import json
		try:
			# Si aún no tienes services.credits, usa requests vía cli:
			import argparse
			from client import cli
			data = cli.cmd_me  # mejor endpoint credits
			import requests
			r = requests.get(
				self._base_url.rstrip("/") + "/me/credits",
				headers={"Authorization": f"Bearer {self._token}"},
				timeout=10,
			)
			r.raise_for_status()
			data = r.json()
		except Exception as exc:
			QMessageBox.critical(self, "Créditos", str(exc))
			return
		total = data.get("total", data.get("totalCredits", "?"))
		lines = [f"Total: {total}", ""]
		for c in data.get("recent") or []:
			if isinstance(c, dict):
				lines.append(
					f"· {c.get('amount', '?')}  task={c.get('task_id', '?')}  "
					f"{c.get('granted_at', '')}"
				)
			else:
				lines.append(str(c))
		QMessageBox.information(self, "Créditos", "\n".join(lines) or "Sin datos")


	def _logout(self) -> None:
		self._stop_auto()
		self._token = None
		self._current_task = None
		self.username_input.clear()
		self.password_input.clear()
		self.stack.setCurrentIndex(self.PAGE_LOGIN)
		self.statusBar().showMessage("Sesión cerrada")

	def closeEvent(self, event) -> None:
		self._stop_auto()
		if self._auto_worker is not None and self._auto_worker.isRunning():
			self._auto_worker.wait(3000)
		super().closeEvent(event)
