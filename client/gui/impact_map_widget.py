"""Mapa de impacto hexagonal (Ártico) — paridad con la APK."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Callable

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from client.gui.i18n import t

COLS = 10
ROWS = 10
HEX_R = 18.0

COLORS = {
    "glacier": QColor(0x5B, 0x9E, 0xA6),
    "gold": QColor(0xFF, 0xB3, 0x00),
    "forest": QColor(0x4C, 0xAF, 0x50),
}
EMPTY_FILL = QColor(0x1A, 0x2F, 0x34)
BORDER = QColor(0x5B, 0x9E, 0xA6, 115)
BG = QColor(0x0D, 0x1B, 0x1E)


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
        self._unlocked: dict[str, dict] = {}  # hex_code upper -> {color, unlocked_at}
        self._offset = QPointF(0, 0)
        self._dragging = False
        self._last_pos = QPointF()
        w, h = _grid_size()
        self.setMinimumSize(int(w), int(h))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_hexes(self, hexes: list[dict]) -> None:
        unlocked: dict[str, dict] = {}
        for h in hexes:
            code = str(h.get("hex_code", "")).upper().strip()
            if not code:
                continue
            unlocked[code] = {
                "color": (h.get("color") or "glacier").lower(),
                "unlocked_at": h.get("unlocked_at") or "",
            }
        self._unlocked = unlocked
        print(f"[impact] canvas unlocked={len(unlocked)} sample={list(unlocked.keys())[:5]}")
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

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._last_pos = event.position()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._dragging:
            delta = event.position() - self._last_pos
            self._offset += delta
            self._last_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._dragging = False

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
    """Card de mapa de impacto (solo scope 'me' por ahora)."""

    refresh_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("impactMapCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        header = QHBoxLayout()
        self.title_label = QLabel(t("impact_map_title"))
        self.title_label.setStyleSheet("font-weight: 700; font-size: 14px;")
        header.addWidget(self.title_label)
        header.addStretch()
        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("font-weight: 700; font-size: 14px; color: #c48a2b;")
        header.addWidget(self.count_label)
        root.addLayout(header)

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

    def set_impact(self, data: dict | None) -> None:
        """data = respuesta de GET /me/impact (o None)."""
        print(f"[impact] set_impact data={data is not None} "
              f"total={(data or {}).get('total_hexes')} "
              f"tiles={len((data or {}).get('tiles') or [])}")

        if not data:
            self.count_label.setText("0")
            self.canvas.set_hexes([])
            self.empty_label.setVisible(True)
            return

        total = int(data.get("total_hexes") or 0)
        hexes: list[dict] = []
        for tile in data.get("tiles") or []:
            hexes.extend(tile.get("hexes") or [])

        if total == 0:
            total = len(hexes)

        self.count_label.setText(str(total))
        self.canvas.set_hexes(hexes)
        print("[impact] label.text=", self.count_label.text(),
              "canvas.id=", id(self.canvas),
              "unlocked=", len(self.canvas._unlocked))
        self.count_label.repaint()
        self.canvas.repaint()
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self.canvas.center_on_latest)



    def retranslate(self) -> None:
        self.title_label.setText(t("impact_map_title"))
        self.hint_label.setText(t("impact_arctic_hint"))
        self.empty_label.setText(t("impact_no_hexes"))
        self.center_btn.setText(t("impact_center"))
