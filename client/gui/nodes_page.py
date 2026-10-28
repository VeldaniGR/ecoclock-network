"""Página de Nodos Ciudadanos para la GUI PyQt6."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from client.gui import services


class NodesPage(QWidget):
    """Pantalla completa de nodos (crear / unirse / mi nodo / explorar)."""

    back_requested = pyqtSignal()  # para volver al dashboard

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("nodesPage")
        self._base_url: str = ""
        self._token: str | None = None
        self._my_node: dict | None = None
        self._public_nodes: list = []

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)

        # Cabecera
        header = QHBoxLayout()
        title = QLabel("Nodos Ciudadanos")
        title.setProperty("class", "brandTitle")
        header.addWidget(title)
        header.addStretch(1)

        self.back_btn = QPushButton("← Volver")
        self.back_btn.setProperty("secondary", True)
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(self.back_btn)
        root.addLayout(header)

        # Área con scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setSpacing(14)
        scroll.setWidget(self.content)
        root.addWidget(scroll, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

    # ------------------------------------------------------------------
    def configure(self, base_url: str, token: str | None) -> None:
        self._base_url = base_url
        self._token = token

    def refresh(self) -> None:
        self.status_label.setText("Cargando...")
        try:
            self._my_node = services.get_my_node(self._base_url, self._token)
        except Exception as e:
            self._my_node = None
            self.status_label.setText(f"Error: {e}")
            return

        try:
            self._public_nodes = services.list_public_nodes(self._base_url, self._token)
        except Exception:
            self._public_nodes = []

        self._rebuild_content()
        self.status_label.setText("")

    # ------------------------------------------------------------------
    def _clear_content(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _rebuild_content(self) -> None:
        self._clear_content()
        if self._my_node:
            self._build_my_node_view()
        else:
            self._build_no_node_view()

    # ========== Con nodo ==========
    def _build_my_node_view(self) -> None:
        node = self._my_node or {}
        is_admin = node.get("my_role") == "admin"

        name = QLabel(node.get("name", ""))
        name.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.content_layout.addWidget(name)

        role = QLabel("Administrador" if is_admin else "Miembro")
        role.setProperty("class", "sectionLabel")
        self.content_layout.addWidget(role)

        self.content_layout.addWidget(
            self._info_row("Miembros", str(node.get("member_count", 0)))
        )

        if is_admin:
            code = node.get("invite_code") or ""
            row = self._info_row("Enlace de unión", code)
            copy_btn = QPushButton("Copiar")
            copy_btn.setProperty("secondary", True)
            copy_btn.clicked.connect(lambda: self._copy(code))
            row.layout().addWidget(copy_btn)
            self.content_layout.addWidget(row)

            del_btn = QPushButton("Eliminar nodo")
            del_btn.setStyleSheet("color: #e05555;")
            del_btn.clicked.connect(self._on_delete)
            self.content_layout.addWidget(del_btn)

        leave_btn = QPushButton("Salir del nodo")
        leave_btn.setStyleSheet("color: #e0a050;")
        leave_btn.clicked.connect(self._on_leave)
        self.content_layout.addWidget(leave_btn)

        self.content_layout.addStretch(1)

    # ========== Sin nodo ==========
    def _build_no_node_view(self) -> None:
        intro = QLabel(
            "Únete a un nodo o crea el tuyo para colaborar con otros ciudadanos."
        )
        intro.setWordWrap(True)
        intro.setProperty("class", "subtitle")
        self.content_layout.addWidget(intro)

        # Crear
        self.content_layout.addWidget(QLabel("Crear un nodo"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nombre del nodo")
        self.content_layout.addWidget(self.name_input)

        create_btn = QPushButton("Crear nodo")
        create_btn.setProperty("primary", True)
        create_btn.clicked.connect(self._on_create)
        self.content_layout.addWidget(create_btn)

        # Unirse por código
        self.content_layout.addSpacing(12)
        self.content_layout.addWidget(QLabel("Unirse con enlace de unión"))
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Ej: QY8RY5LD")
        self.content_layout.addWidget(self.code_input)

        join_btn = QPushButton("Unirse al nodo")
        join_btn.setProperty("secondary", True)
        join_btn.clicked.connect(self._on_join)
        self.content_layout.addWidget(join_btn)

        # Públicos
        self.content_layout.addSpacing(12)
        self.content_layout.addWidget(QLabel("Explorar nodos públicos"))

        if not self._public_nodes:
            empty = QLabel("No hay nodos públicos todavía.")
            empty.setProperty("class", "subtitle")
            self.content_layout.addWidget(empty)
        else:
            for n in self._public_nodes:
                self.content_layout.addWidget(self._public_card(n))

        self.content_layout.addStretch(1)

    def _public_card(self, n: dict) -> QWidget:
        frame = QFrame()
        frame.setProperty("class", "statCard")
        lay = QHBoxLayout(frame)

        info = QVBoxLayout()
        info.addWidget(QLabel(n.get("name", "")))
        members = QLabel(f"{n.get('member_count', 0)} miembros")
        members.setProperty("class", "sectionLabel")
        info.addWidget(members)
        lay.addLayout(info, stretch=1)

        req_btn = QPushButton("Solicitar")
        req_btn.setProperty("secondary", True)
        node_id = n.get("id")
        name = n.get("name", "")
        req_btn.clicked.connect(lambda: self._on_request(node_id, name))
        lay.addWidget(req_btn)
        return frame

    def _info_row(self, label: str, value: str) -> QWidget:
        frame = QFrame()
        frame.setProperty("class", "statCard")
        lay = QHBoxLayout(frame)
        col = QVBoxLayout()
        col.addWidget(QLabel(label))
        val = QLabel(value)
        val.setStyleSheet("font-weight: 600;")
        col.addWidget(val)
        lay.addLayout(col, stretch=1)
        return frame

    # ---------- acciones ----------
    def _copy(self, text: str) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        self.status_label.setText("Código copiado")

    def _on_create(self) -> None:
        name = self.name_input.text().strip()
        if len(name) < 3:
            QMessageBox.warning(self, "Nodo", "El nombre debe tener al menos 3 caracteres.")
            return
        try:
            self._my_node = services.create_node(self._base_url, name, self._token)
            self._rebuild_content()
            self.status_label.setText("Nodo creado")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_join(self) -> None:
        code = self.code_input.text().strip().upper()
        if not code:
            return
        try:
            self._my_node = services.join_node_by_code(self._base_url, code, self._token)
            self._rebuild_content()
            self.status_label.setText("Te has unido al nodo")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_leave(self) -> None:
        if QMessageBox.question(self, "Salir", "¿Salir del nodo?") != QMessageBox.StandardButton.Yes:
            return
        try:
            services.leave_node(self._base_url, self._token)
            self._my_node = None
            self.refresh()
            self.status_label.setText("Has salido del nodo")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_delete(self) -> None:
        node = self._my_node or {}
        if QMessageBox.question(
            self, "Eliminar",
            f"¿Eliminar permanentemente \"{node.get('name')}\"?",
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            services.delete_node(self._base_url, node["id"], self._token)
            self._my_node = None
            self.refresh()
            self.status_label.setText("Nodo eliminado")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_request(self, node_id: int, name: str) -> None:
        try:
            services.request_join_node(self._base_url, node_id, self._token)
            self.status_label.setText(f'Solicitud enviada a "{name}"')
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
