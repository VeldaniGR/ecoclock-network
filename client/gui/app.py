"""Ventana principal de Eco'clock (Fase 2). Scaffold minimo: QMainWindow con un QLabel y un QPushButton de salida."""


import sys



def main(argv: list[str] | None = None) -> int:

	# Import perezoso: si PyQt6 no esta instalado, este modulo aun es

	# importable; el error se lanza solo al ejecutar la GUI.

	app = QApplication(argv if argv is not None else sys.argv)
	window = QMainWindow()
	window.setWindowTitle("Eco'clock")
	window.resize(480, 320)
	window.setMinimumSize(320, 240)
	# Centrar en pantalla
	screen = app.primaryScreen().availableGeometry()
	window.move(screen.center().x() - window.width() // 2, screen.center().y() - window.height() // 2)
	central = QWidget(window)
	layout = QVBoxLayout(central)
	label = QLabel("Ecoclock  Fase 2 (scaffold)", central)
	label.setAlignment(Qt.AlignmentFlag.AlignCenter)
	layout.addWidget(label)
	button = QPushButton("Salir", central)
	button.setToolTip("Cierra la aplicacion (atajo: Ctrl+Q)")
	button.clicked.connect(app.quit)
	layout.addWidget(button)
	window.setCentralWidget(central)

	# Menu basico con atajo de salida
	quit_action = QAction("&Salir", window)
	quit_action.setShortcut("Ctrl+Q")
	quit_action.triggered.connect(app.quit)
	menu = window.menuBar().addMenu("&Archivo")
	menu.addAction(quit_action)
	window.statusBar().showMessage("Listo")
	window.show()

	return app.exec()
