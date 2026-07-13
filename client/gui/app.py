"""Ventana principal de Eco'clock (Fase 2). Scaffold minimo: QMainWindow con un QLabel y un QPushButton de salida.
La logica real (mostrar tareas, NDVI, login, etc.) se aniade en commits posteriores sin tocar el entry point del CLI."""
from __future__ import annotations
import sys


def main(argv: list[str] | None = None) -> int:
	# Import perezoso: si PyQt6 no esta instalado, este modulo aun es
	# importable; el error se lanza solo al ejecutar la GUI.
	from PyQt6.QtCore import Qt
	from PyQt6.QtGui import QAction
	from PyQt6.QtWidgets import (
		QApplication,
		QLabel,
		QMainWindow,
		QPushButton,
		QVBoxLayout,
		QWidget,
	)

	app = QApplication(argv if argv is not None else sys.argv)
	window = QMainWindow()
	window.setWindowTitle("Eco'clock")
	window.resize(480, 320)
	central = QWidget(window)
	layout = QVBoxLayout(central)
	label = QLabel("Ecoclock  Fase 2 (scaffold)", central)
	label.setAlignment(Qt.AlignmentFlag.AlignCenter)
	layout.addWidget(label)
	button = QPushButton("Salir", central)
	button.clicked.connect(app.quit)
	layout.addWidget(button)
	window.setCentralWidget(central)

	# Menu basico con atajo de salida
	quit_action = QAction("&Salir", window)
	quit_action.setShortcut("Ctrl+Q")
	quit_action.triggered.connect(app.quit)
	menu = window.menuBar().addMenu("&Archivo")
	menu.addAction(quit_action)
	window.show()

	return app.exec()
