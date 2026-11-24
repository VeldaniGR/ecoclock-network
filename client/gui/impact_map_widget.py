"""Mapa de impacto hexagonal (Ártico) — paridad con la APK.

Tres ámbitos:
  - "me":      los hexágonos del usuario (GET /me/impact).
  - "node":    los de su nodo.
  - "network": los de toda la red.

En "node" y "network" cada hexágono lleva `count` (cuántos participantes lo han
desbloqueado) y la intensidad del color crece con ese número. Los datos de esos
dos ámbitos los pide quien use el widget: el widget emite `scope_requested` y
quien lo escucha responde con `set_scope_data(...)` o `set_scope_error(...)`.
"""
from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from client.gui.i18n import t

COLS = 10
ROWS = 10
HEX_R = 18.0
SCOPES = ("me", "node", "network")

COLORS = {
    "glacier": QColor(0x5B, 0x9E, 0xA6),
    "gold": QColor(0xFF, 0xB3, 0x00),
    "forest": QColor(0x4C, 0xAF, 0x50),
}
EMPTY_FILL = QColor(0x1A, 0x2F, 0x34)
BORDER = QColor(0x5B, 0x9E, 0xA6, 115)
BG = QColor(0x0D, 0x1B, 0x1E)


def _tr(key: str, default: str) -> str:
    """Traducción con texto de reserva: no falla si la clave aún no está en i18n."""
    try:
        text = t(key)
    except Exception:
        return default
    return default if not text or text == key else text


def _parse_hex(code: str) -> tuple[int, int] | None:
    if not code:
        return None
    letter = code[0].upper()
    try:
        col = int(code[1:])
    except ValueError:
        return None
    if col < 1 or col > COLS:
        return None
    row = ord(letter) - ord("A")
    if row < 0 or row >= ROWS:
        return None
    return col - 1, row


def _grid_size(hex_r: float = HEX_R) -> tuple[float, float]:
    horiz = hex_r * math.sqrt(3)
    vert = hex_r * 1.5
    w = (COLS - 1) * horiz + 2 * hex_r + 24
    h = (ROWS - 1) * vert + 2 * hex_r + 24
    return w, h


class _HexCanvas(QWidget):
    """Lienzo con la rejilla de hexágonos."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # hex_code en mayúsculas -> {color, unlocked_at, count}
        self._unlocked: dict[str, dict] = {}
        self._max_count = 1
        self._show_counts = False
        self._offset = QPointF(0, 0)
        self._dragging = False
        self._last_pos = QPointF()
        self.setMouseTracking(True)  # para el tooltip al pasar el ratón
        w, h = _grid_size()
        self.setMinimumSize(int(w), int(h))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_hexes(self, hexes: list[dict], show_counts: bool = False) -> None:
        unlocked: dict[str, dict] = {}
        for h in hexes:
            code = str(h.get("hex_code", "")).upper().strip()
            if not code:
                continue
            try:
                count = max(1, int(h.get("count") or 1))
            except (TypeError, ValueError):
                count = 1
            unlocked[code] = {
                "color": (h.get("color") or "glacier").lower(),
                "unlocked_at": h.get("unlocked_at") or "",
                "count": count,
            }
        self._unlocked = unlocked
        self._show_counts = show_counts
        self._max_count = max((v["count"] for v in unlocked.values()), default=1)
        self.update()

    def center_on_latest(self) -> None:
        gw, gh = _grid_size()
        vw = max(self.width(), 1)
        vh = max(self.height(), 1)
        # Si aún no hay tamaño real, no desplazar
        if vw < 50 or vh < 50:
            self._offset = QPointF(0, 0)
        else:
            self._offset = QPointF((vw - gw) / 2.0, (vh - gh) / 2.0)
        self.update()

    def _hex_at(self, pos: QPointF) -> str | None:
        """Código del hexágono bajo el cursor, o None."""
        x = pos.x() - self._offset.x()
        y = pos.y() - self._offset.y()
        horiz = HEX_R * math.sqrt(3)
        vert = HEX_R * 1.5
        ox = oy = 12.0 + HEX_R
        best = None
        best_d = (HEX_R * 0.9) ** 2
        for row in range(ROWS):
            for col in range(COLS):
                cx = ox + col * horiz + (horiz / 2 if row % 2 else 0.0)
                cy = oy + row * vert
                d = (x - cx) ** 2 + (y - cy) ** 2
                if d < best_d:
                    best_d = d
                    best = f"{chr(ord('A') + row)}{col + 1}"
        return best

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._last_pos = event.position()
            QToolTip.hideText()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._dragging:
            delta = event.position() - self._last_pos
            self._offset += delta
            self._last_pos = event.position()
            self.update()
            return
        if not self._show_counts:
            return
        code = self._hex_at(event.position())
        hit = self._unlocked.get(code) if code else None
        if hit:
            people = _tr("impact_participants", "{n} participantes").replace(
                "{n}", str(hit["count"])
            )
            QToolTip.showText(event.globalPosition().toPoint(), f"{code} · {people}", self)
        else:
            QToolTip.hideText()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._dragging = False

    def leaveEvent(self, event) -> None:  # noqa: N802
        QToolTip.hideText()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), BG)
        p.translate(self._offset)

        horiz = HEX_R * math.sqrt(3)
        vert = HEX_R * 1.5
        ox = 12.0 + HEX_R
        oy = 12.0 + HEX_R

        font = QFont()
        font.setPointSize(7)
        font.setBold(True)
        p.setFont(font)

        for row in range(ROWS):
            for col in range(COLS):
                code = f"{chr(ord('A') + row)}{col + 1}"
                offset_x = horiz / 2 if row % 2 else 0.0
                cx = ox + col * horiz + offset_x
                cy = oy + row * vert
                path = self._hex_path(cx, cy, HEX_R)

                hit = self._unlocked.get(code)
                if hit:
                    color = COLORS.get(hit["color"], COLORS["glacier"])
                    fill = QColor(color)
                    if self._show_counts and self._max_count > 1:
                        # Más participantes = más intensidad (de 0,40 a 0,85)
                        fill.setAlphaF(0.40 + 0.45 * hit["count"] / self._max_count)
                    else:
                        fill.setAlphaF(0.85)
                    p.fillPath(path, fill)
                    pen = QPen(color)
                    pen.setWidthF(1.6)
                    p.setPen(pen)
                    p.drawPath(path)
                    p.setPen(QColor(255, 255, 255))
                else:
                    p.fillPath(path, EMPTY_FILL)
                    pen = QPen(BORDER)
                    pen.setWidthF(1.2)
                    p.setPen(pen)
                    p.drawPath(path)
                    p.setPen(QColor(255, 255, 255, 100))

                br = p.fontMetrics().boundingRect(code)
                p.drawText(
                    QRectF(cx - br.width() / 2 - 2, cy - br.height() / 2, br.width() + 4, br.height()),
                    Qt.AlignmentFlag.AlignCenter,
                    code,
                )

        p.end()

    @staticmethod
    def _hex_path(cx: float, cy: float, r: float) -> QPainterPath:
        path = QPainterPath()
        for i in range(6):
            angle = -math.pi / 6 + i * math.pi / 3
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        path.closeSubpath()
        return path


class ImpactMapWidget(QFrame):
    """Card de mapa de impacto con ámbitos: yo, mi nodo y red."""

    refresh_requested = pyqtSignal()
    # Se emite al abrir la pestaña "node" o "network": quien lo escuche debe pedir
    # los datos y responder con set_scope_data() o set_scope_error()
    scope_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("impactMapCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self._scope = "me"
        self._data: dict[str, dict | None] = {s: None for s in SCOPES}

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        # Cabecera: título + contador
        header = QHBoxLayout()
        self.title_label = QLabel(t("impact_map_title"))
        self.title_label.setStyleSheet("font-weight: 700; font-size: 14px;")
        header.addWidget(self.title_label)
        header.addStretch()
        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("font-weight: 700; font-size: 14px; color: #c48a2b;")
        header.addWidget(self.count_label)
        root.addLayout(header)

        # Pestañas de ámbito
        tabs_row = QHBoxLayout()
        tabs_row.setSpacing(6)
        self._scope_group = QButtonGroup(self)
        self._scope_group.setExclusive(True)

        self.tab_me = QPushButton(t("impact_tab_me"))
        self.tab_node = QPushButton(t("impact_tab_node"))
        self.tab_network = QPushButton(t("impact_tab_network"))
        for i, btn in enumerate((self.tab_me, self.tab_node, self.tab_network)):
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("scopeTab", True)
            self._scope_group.addButton(btn, i)
            tabs_row.addWidget(btn)
        tabs_row.addStretch(1)
        self.tab_me.setChecked(True)
        self._scope_group.idClicked.connect(self._on_scope_changed)
        root.addLayout(tabs_row)

        self.scope_msg = QLabel("")
        self.scope_msg.setWordWrap(True)
        self.scope_msg.setStyleSheet("color: #8a7a66; font-size: 12px;")
        self.scope_msg.setVisible(False)
        root.addWidget(self.scope_msg)

        self.hint_label = QLabel(t("impact_arctic_hint"))
        self.hint_label.setStyleSheet("color: #8a7a66; font-size: 11px;")
        root.addWidget(self.hint_label)

        self.canvas = _HexCanvas(self)
        self.canvas.setMinimumHeight(280)
        root.addWidget(self.canvas)

        footer = QHBoxLayout()
        self.empty_label = QLabel(t("impact_no_hexes"))
        self.empty_label.setStyleSheet("color: #8a7a66; font-size: 12px;")
        self.empty_label.setVisible(False)
        footer.addWidget(self.empty_label)
        footer.addStretch()
        self.center_btn = QPushButton(t("impact_center"))
        self.center_btn.setObjectName("secondaryButton")
        self.center_btn.clicked.connect(self.canvas.center_on_latest)
        footer.addWidget(self.center_btn)
        root.addLayout(footer)

    # ----------------------------------------------------------- datos

    def set_impact(self, data: dict | None) -> None:
        """Ámbito "me": data = respuesta de GET /me/impact (o None)."""
        self.set_scope_data("me", data)

    def set_scope_data(self, scope: str, data: dict | None) -> None:
        """Guarda los datos de un ámbito y, si es el visible, lo dibuja.

        Para "node" y "network", data tiene esta forma:
            {"node": {"id": 1, "name": "..."} | None,   # solo en "node"
             "participants": 2, "total_hexes": 14,
             "hexes": [{"hex_code": "D6", "color": "glacier", "count": 2,
                        "unlocked_at": "..."}]}
        """
        if scope not in SCOPES:
            return
        self._data[scope] = data
        if scope == self._scope:
            self._render()

    def set_scope_error(self, scope: str, message: str | None = None) -> None:
        """Avisa de un fallo al cargar un ámbito (se conserva lo que hubiera dibujado)."""
        if scope != self._scope:
            return
        self._show_msg(message or _tr("impact_scope_error", "No se pudo cargar. Inténtalo de nuevo."))

    def clear_scopes(self) -> None:
        """Olvida los datos de nodo y red (llamar al cerrar sesión o cambiar de cuenta)."""
        self._data["node"] = None
        self._data["network"] = None
        if self._scope != "me":
            self._render()

    # --------------------------------------------------------- dibujado

    def _show_msg(self, text: str) -> None:
        self.scope_msg.setText(text)
        self.scope_msg.setVisible(bool(text))

    @staticmethod
    def _flatten_me(data: dict | None) -> tuple[list[dict], int]:
        if not data:
            return [], 0
        hexes: list[dict] = []
        for tile in data.get("tiles") or []:
            hexes.extend(tile.get("hexes") or [])
        total = int(data.get("total_hexes") or 0) or len(hexes)
        return hexes, total

    def _summary(self, scope: str, data: dict) -> str:
        people = _tr("impact_participants", "{n} participantes").replace(
            "{n}", str(int(data.get("participants") or 0))
        )
        if scope == "node":
            name = (data.get("node") or {}).get("name") or ""
            return f"{name} · {people}" if name else people
        return people

    def _render(self) -> None:
        scope = self._scope
        data = self._data.get(scope)
        self.hint_label.setVisible(scope == "me")
        self.canvas.setVisible(True)
        self.center_btn.setVisible(True)
        self._show_msg("")

        if scope == "me":
            hexes, total = self._flatten_me(data)
            self.canvas.set_hexes(hexes, show_counts=False)
            self.count_label.setText(str(total))
            self.empty_label.setVisible(len(hexes) == 0)
            QTimer.singleShot(0, self.canvas.center_on_latest)
            return

        if data is None:  # todavía cargando
            self.canvas.set_hexes([], show_counts=True)
            self.count_label.setText("…")
            self.empty_label.setVisible(False)
            self._show_msg(_tr("impact_scope_loading", "Cargando…"))
            return

        if scope == "node" and not data.get("node"):
            self.canvas.setVisible(False)
            self.center_btn.setVisible(False)
            self.count_label.setText("0")
            self.empty_label.setVisible(False)
            self._show_msg(_tr("impact_no_node", "Aún no perteneces a ningún nodo."))
            return

        hexes = data.get("hexes") or []
        total = int(data.get("total_hexes") or 0) or len(hexes)
        self.canvas.set_hexes(hexes, show_counts=True)
        self.count_label.setText(str(total))
        self.empty_label.setVisible(len(hexes) == 0)
        self._show_msg(self._summary(scope, data))
        QTimer.singleShot(0, self.canvas.center_on_latest)

    def _on_scope_changed(self, idx: int) -> None:
        self._scope = SCOPES[idx]
        self._render()
        if self._scope != "me":
            # Se vuelve a pedir cada vez: mientras llega, se ve lo último que hubiera
            self.scope_requested.emit(self._scope)

    def retranslate(self) -> None:
        self.title_label.setText(t("impact_map_title"))
        self.hint_label.setText(t("impact_arctic_hint"))
        self.empty_label.setText(t("impact_no_hexes"))
        self.center_btn.setText(t("impact_center"))
        self.tab_me.setText(t("impact_tab_me"))
        self.tab_node.setText(t("impact_tab_node"))
        self.tab_network.setText(t("impact_tab_network"))
        self._render()
