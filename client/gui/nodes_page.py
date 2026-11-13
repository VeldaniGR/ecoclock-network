"""Página de Nodos Ciudadanos para la GUI PyQt6."""
from __future__ import annotations

import json

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QButtonGroup
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from client.gui import services
from client.gui.i18n import t
from client.gui.frames import load_frame_pixmap, parse_unlocked_frames
from client.gui.frames import make_logo_with_frame


FRAME_STYLES = {
    "autumn_fungi": "border: 3px solid #C4A35A; border-radius: 14px; padding: 2px;",
    "arctic_ice": (
        "border: 3px solid #7EC8E3; border-radius: 14px; padding: 2px;"
        "background-color: rgba(126, 200, 227, 0.12);"
    ),
    "deforestation": "border: 3px solid #6B8F3C; border-radius: 14px; padding: 2px;",
    "energy": "border: 3px solid #E0A030; border-radius: 14px; padding: 2px;",
    "environmental_crime": "border: 3px solid #B04040; border-radius: 14px; padding: 2px;",
    "ozone": "border: 3px solid #5B9EA6; border-radius: 14px; padding: 2px;",
    "posidonia": "border: 3px solid #2E8B7A; border-radius: 14px; padding: 2px;",
    "sea_ice": "border: 3px solid #A8D4E6; border-radius: 14px; padding: 2px;",
    "water": "border: 3px solid #3A7CA5; border-radius: 14px; padding: 2px;",
}


class NodesPage(QWidget):
    back_requested = pyqtSignal()
    frame_changed = pyqtSignal(dict)  # NodeDetail actualizado → dashboard

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("nodesPage")
        self._base_url: str = ""
        self._token: str | None = None
        self._my_node: dict | None = None
        self._public_nodes: list = []
        self._members: list = []
        self._join_requests: list = []
        self._frame_buttons: list[QPushButton] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)

        header = QHBoxLayout()
        self.title_label = QLabel(t("nodes_title"))
        self.title_label.setProperty("class", "brandTitle")
        header.addWidget(self.title_label)
        header.addStretch(1)
        self.back_btn = QPushButton(t("nodes_back"))
        self.back_btn.setProperty("secondary", True)
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(self.back_btn)
        root.addLayout(header)

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

    def configure(self, base_url: str, token: str | None) -> None:
        self._base_url = base_url
        self._token = token

    def refresh(self) -> None:
        self.status_label.setText(t("nodes_loading"))
        try:
            self._my_node = services.get_my_node(self._base_url, self._token)
        except Exception as e:
            self._my_node = None
            self._members = []
            self._join_requests = []
            self.status_label.setText(f"{t('error')}: {e}")
            self._rebuild_content()
            return

        try:
            self._public_nodes = services.list_public_nodes(self._base_url, self._token)
        except Exception:
            self._public_nodes = []

        self._members = []
        self._join_requests = []
        if self._my_node:
            nid = self._my_node.get("id")
            try:
                self._members = services.list_node_members(
                    self._base_url, nid, self._token
                )
            except Exception:
                self._members = []
            if self._my_node.get("my_role") == "admin":
                try:
                    reqs = services.list_join_requests(
                        self._base_url, nid, self._token
                    )
                    self._join_requests = [
                        r for r in reqs if r.get("status") == "pending"
                    ]
                except Exception:
                    self._join_requests = []

        self._rebuild_content()
        self.status_label.setText("")

    def _clear_content(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._frame_buttons = []

    def _rebuild_content(self) -> None:
        self._clear_content()
        if self._my_node:
            self._build_my_node_view()
        else:
            self._build_no_node_view()

    def _unlocked_frames(self, node: dict) -> list[str]:
        return parse_unlocked_frames(node.get("unlocked_frames"))

    def _load_logo_pixmap(self, logo_url: str | None) -> QPixmap:
        pix = QPixmap(64, 64)
        pix.fill(Qt.GlobalColor.transparent)
        if not logo_url:
            return pix
        full = (
            logo_url
            if logo_url.startswith("http")
            else f"{self._base_url.rstrip('/')}{logo_url}"
        )
        try:
            import requests

            data = requests.get(full, timeout=10).content
            pix.loadFromData(data)
        except Exception:
            pass
        return pix

    def _frame_label(self, key: str) -> str:
        if not key:
            return t("nodes_frame_none")
        # fallback al id si no hay clave i18n
        translated = t(f"frame_{key}")
        if translated == f"frame_{key}":
            return key.replace("_", " ").title()
        return translated

    def _build_my_node_view(self) -> None:
        node = self._my_node or {}
        is_admin = node.get("my_role") == "admin"
        frame = node.get("logo_frame") or ""

        columns = QHBoxLayout()
        columns.setSpacing(24)

        # ══════════════════════════════════════════
        # IZQUIERDA — gestión
        # ══════════════════════════════════════════
        left = QVBoxLayout()
        left.setSpacing(12)

        if is_admin:
            # Marco del logo
            left.addWidget(QLabel(t("nodes_frame")))
            unlocked = self._unlocked_frames(node)
            if not unlocked:
                hint = QLabel(t("nodes_frame_hint"))
                hint.setProperty("class", "sectionLabel")
                left.addWidget(hint)
            else:
                frames_wrap = QWidget()
                frames_lay = QHBoxLayout(frames_wrap)
                frames_lay.setContentsMargins(0, 0, 0, 0)
                frames_lay.setSpacing(8)

                group = QButtonGroup(self)
                group.setExclusive(True)

                none_btn = QPushButton(t("nodes_frame_none"))
                none_btn.setCheckable(True)
                none_btn.setChecked(not frame)
                none_btn.setProperty("frameId", "")
                none_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                group.addButton(none_btn)
                none_btn.clicked.connect(lambda: self._on_frame_changed(None))
                frames_lay.addWidget(none_btn)
                self._frame_buttons.append(none_btn)

                for fid in unlocked:
                    btn = QPushButton()
                    btn.setCheckable(True)
                    btn.setChecked(fid == frame)
                    btn.setFixedSize(64, 64)
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.setProperty("frameId", fid)
                    btn.setToolTip(self._frame_label(fid))
                    ipix = load_frame_pixmap(fid, 56)
                    if not ipix.isNull():
                        btn.setIcon(QIcon(ipix))
                        btn.setIconSize(ipix.size())
                    else:
                        btn.setText(fid[:8])
                    group.addButton(btn)
                    btn.clicked.connect(lambda _=False, f=fid: self._on_frame_changed(f))
                    frames_lay.addWidget(btn)
                    self._frame_buttons.append(btn)

                frames_lay.addStretch(1)
                left.addWidget(frames_wrap)

            # Acciones de admin
            actions = QHBoxLayout()
            logo_btn = QPushButton(t("nodes_change_logo"))
            logo_btn.setProperty("secondary", True)
            logo_btn.clicked.connect(self._on_change_logo)
            actions.addWidget(logo_btn)

            rename_btn = QPushButton(t("nodes_rename"))
            rename_btn.setProperty("secondary", True)
            rename_btn.clicked.connect(self._on_rename)
            actions.addWidget(rename_btn)
            actions.addStretch(1)
            left.addLayout(actions)

            # Enlace de unión
            code = node.get("invite_code") or ""
            row = self._info_row(t("nodes_invite"), code)
            copy_btn = QPushButton(t("nodes_copy"))
            copy_btn.setProperty("secondary", True)
            copy_btn.clicked.connect(lambda: self._copy(code))
            row.layout().addWidget(copy_btn)
            left.addWidget(row)

            # Solicitudes
            left.addSpacing(6)
            left.addWidget(QLabel(t("nodes_requests")))
            if not self._join_requests:
                empty = QLabel(t("nodes_no_requests"))
                empty.setProperty("class", "sectionLabel")
                left.addWidget(empty)
            else:
                for r in self._join_requests:
                    left.addWidget(self._request_row(r))

        # Miembros (todos)
        left.addSpacing(6)
        left.addWidget(
            QLabel(f"{t('nodes_members')} ({node.get('member_count', 0)})")
        )
        if not self._members:
            empty = QLabel("—")
            empty.setProperty("class", "sectionLabel")
            left.addWidget(empty)
        else:
            for m in self._members:
                left.addWidget(self._member_row(m, is_admin))

        # Salir / eliminar
        left.addSpacing(8)
        leave_btn = QPushButton(t("nodes_leave"))
        leave_btn.setStyleSheet("color: #e0a050;")
        leave_btn.clicked.connect(self._on_leave)
        left.addWidget(leave_btn)

        if is_admin:
            del_btn = QPushButton(t("nodes_delete"))
            del_btn.setStyleSheet("color: #e05555;")
            del_btn.clicked.connect(self._on_delete)
            left.addWidget(del_btn)

        left.addStretch(1)
        left_w = QWidget()
        left_w.setLayout(left)

        # ══════════════════════════════════════════
        # DERECHA — identidad
        # ══════════════════════════════════════════
        right = QVBoxLayout()
        right.setSpacing(12)
        right.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter
        )

        from client.gui.frames import make_logo_with_frame

        pix = self._load_logo_pixmap(node.get("logo_url"))
        badge = make_logo_with_frame(pix, frame, size=120)
        right.addWidget(badge, alignment=Qt.AlignmentFlag.AlignHCenter)

        name = QLabel(node.get("name", ""))
        name.setStyleSheet("font-size: 20px; font-weight: 700;")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(name)

        role = QLabel(t("nodes_admin") if is_admin else t("nodes_member"))
        role.setProperty("class", "sectionLabel")
        role.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(role)

        # Placeholder hasta backend description
        desc = QLabel("Descripción del nodo (próximamente)")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #8a7a66; font-size: 12px;")
        desc.setMaximumWidth(220)
        right.addWidget(desc, alignment=Qt.AlignmentFlag.AlignHCenter)

        right.addStretch(1)
        right_w = QWidget()
        right_w.setLayout(right)
        right_w.setMinimumWidth(260)

        columns.addWidget(left_w, stretch=3)
        columns.addWidget(right_w, stretch=2)
        self.content_layout.addLayout(columns)

    def _request_row(self, r: dict) -> QWidget:
        frame = QFrame()
        frame.setProperty("class", "statCard")
        lay = QHBoxLayout(frame)
        lay.addWidget(QLabel(r.get("username") or "—"), stretch=1)
        rid = r.get("id")
        acc = QPushButton(t("nodes_accept"))
        acc.setProperty("primary", True)
        acc.clicked.connect(lambda: self._on_accept(rid))
        rej = QPushButton(t("nodes_reject"))
        rej.setProperty("secondary", True)
        rej.clicked.connect(lambda: self._on_reject(rid))
        lay.addWidget(acc)
        lay.addWidget(rej)
        return frame

    def _member_row(self, m: dict, is_admin: bool) -> QWidget:
        frame = QFrame()
        frame.setProperty("class", "statCard")
        lay = QHBoxLayout(frame)
        username = m.get("username") or ""
        role = m.get("role") or "member"
        uid = m.get("user_id")
        role_txt = t("nodes_admin") if role == "admin" else t("nodes_member")
        lay.addWidget(QLabel(f"{username} · {role_txt}"), stretch=1)
        if is_admin and role != "admin":
            tr = QPushButton(t("nodes_transfer"))
            tr.setProperty("secondary", True)
            tr.clicked.connect(lambda: self._on_transfer(uid, username))
            kick = QPushButton(t("nodes_kick"))
            kick.setStyleSheet("color: #e05555;")
            kick.clicked.connect(lambda: self._on_kick(uid, username))
            lay.addWidget(tr)
            lay.addWidget(kick)
        return frame

    def _build_no_node_view(self) -> None:
        intro = QLabel(t("nodes_intro"))
        intro.setWordWrap(True)
        intro.setProperty("class", "subtitle")
        self.content_layout.addWidget(intro)

        self.content_layout.addWidget(QLabel(t("nodes_create")))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t("nodes_name_ph"))
        self.content_layout.addWidget(self.name_input)
        create_btn = QPushButton(t("nodes_create_btn"))
        create_btn.setProperty("primary", True)
        create_btn.clicked.connect(self._on_create)
        self.content_layout.addWidget(create_btn)

        self.content_layout.addSpacing(12)
        self.content_layout.addWidget(QLabel(t("nodes_join_code")))
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText(t("nodes_code_ph"))
        self.content_layout.addWidget(self.code_input)
        join_btn = QPushButton(t("nodes_join_btn"))
        join_btn.setProperty("secondary", True)
        join_btn.clicked.connect(self._on_join)
        self.content_layout.addWidget(join_btn)

        self.content_layout.addSpacing(12)
        self.content_layout.addWidget(QLabel(t("nodes_explore")))
        if not self._public_nodes:
            empty = QLabel(t("nodes_no_public"))
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
        members = QLabel(f"{n.get('member_count', 0)} {t('nodes_members').lower()}")
        members.setProperty("class", "sectionLabel")
        info.addWidget(members)
        lay.addLayout(info, stretch=1)
        req_btn = QPushButton(t("nodes_request_join"))
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

    def _copy(self, text: str) -> None:
        from PyQt6.QtWidgets import QApplication

        QApplication.clipboard().setText(text)
        self.status_label.setText(t("copied"))

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def _on_create(self) -> None:
        name = self.name_input.text().strip()
        if len(name) < 3:
            QMessageBox.warning(
                self, t("error"), "El nombre debe tener al menos 3 caracteres."
            )
            return
        try:
            self._my_node = services.create_node(self._base_url, name, self._token)
            self.refresh()
            self.status_label.setText("Nodo creado")
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _on_join(self) -> None:
        code = self.code_input.text().strip().upper()
        if not code:
            return
        try:
            self._my_node = services.join_node_by_code(
                self._base_url, code, self._token
            )
            self.refresh()
            self.status_label.setText("Te has unido al nodo")
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _on_leave(self) -> None:
        if (
            QMessageBox.question(self, t("nodes_leave"), t("confirm_leave"))
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            services.leave_node(self._base_url, self._token)
            self._my_node = None
            self.refresh()
            self.status_label.setText("Has salido del nodo")
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _on_delete(self) -> None:
        node = self._my_node or {}
        if (
            QMessageBox.question(self, t("nodes_delete"), t("confirm_delete"))
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            services.delete_node(self._base_url, node["id"], self._token)
            self._my_node = None
            self.refresh()
            self.status_label.setText("Nodo eliminado")
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _on_request(self, node_id: int, name: str) -> None:
        try:
            services.request_join_node(self._base_url, node_id, self._token)
            self.status_label.setText(f'Solicitud enviada a "{name}"')
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _on_change_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("nodes_change_logo"), "", "Imágenes (*.png *.jpg *.jpeg)"
        )
        if not path:
            return
        node = self._my_node or {}
        try:
            result = services.upload_node_logo(
                self._base_url, node["id"], path, self._token
            )
            self._my_node = {**node, "logo_url": result.get("logo_url")}
            self._rebuild_content()
            self.status_label.setText("Logo actualizado")
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _on_rename(self) -> None:
        node = self._my_node or {}
        name, ok = QInputDialog.getText(
            self, t("nodes_rename"), "Nuevo nombre:", text=node.get("name", "")
        )
        if not ok or len(name.strip()) < 3:
            return
        try:
            updated = services.update_node(
                self._base_url, node["id"], self._token, name=name.strip()
            )
            self._my_node = updated
            self._rebuild_content()
            self.status_label.setText("Nombre actualizado")
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _on_frame_changed(self, frame_id) -> None:
        node = self._my_node or {}
        try:
            updated = services.update_node(
                self._base_url,
                node["id"],
                self._token,
                logo_frame=frame_id if frame_id else "none",
            )
            self._my_node = {**node, **updated}
            self._rebuild_content()
            self.status_label.setText("Marco actualizado")
            self.frame_changed.emit(self._my_node)
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _on_accept(self, request_id: int) -> None:
        node = self._my_node or {}
        try:
            services.accept_join_request(
                self._base_url, node["id"], request_id, self._token
            )
            self.refresh()
            self.status_label.setText("Solicitud aceptada")
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _on_reject(self, request_id: int) -> None:
        node = self._my_node or {}
        try:
            services.reject_join_request(
                self._base_url, node["id"], request_id, self._token
            )
            self.refresh()
            self.status_label.setText("Solicitud rechazada")
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _on_kick(self, user_id: int, username: str) -> None:
        node = self._my_node or {}
        if (
            QMessageBox.question(
                self, t("nodes_kick"), t("confirm_kick", user=username)
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            services.kick_member(self._base_url, node["id"], user_id, self._token)
            self.refresh()
            self.status_label.setText(f"{username} expulsado")
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))

    def _on_transfer(self, user_id: int, username: str) -> None:
        node = self._my_node or {}
        if (
            QMessageBox.question(
                self,
                t("nodes_transfer"),
                t("confirm_transfer", user=username),
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            services.transfer_leadership(
                self._base_url, node["id"], user_id, self._token
            )
            self.refresh()
            self.status_label.setText(f"Liderazgo transferido a {username}")
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e))