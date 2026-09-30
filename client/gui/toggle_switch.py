"""Interruptor deslizante (pill + círculo), estilo 'Activar'."""
from __future__ import annotations

from PyQt6.QtCore import QPropertyAnimation, QRectF, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import QWidget


class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, label: str = "Activar", parent=None) -> None:
        super().__init__(parent)
        self._label = label
        self._checked = False
        self._offset = 0.0  # 0 = off, 1 = on
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(40)
        self.setMinimumWidth(200)

        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(160)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool, *, animate: bool = True) -> None:
        if self._checked == checked:
            return
        self._checked = checked
        end = 1.0 if checked else 0.0
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._offset)
            self._anim.setEndValue(end)
            self._anim.start()
        else:
            self._offset = end
            self.update()
        self.toggled.emit(self._checked)

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = pyqtProperty(float, get_offset, set_offset)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
        super().mousePressEvent(event)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        margin = 2.0
        radius = (h - 2 * margin) / 2.0

        # Fondo píldora
        bg = QColor("#2a2a24") if not self._checked else QColor("#3d5a40")
        path = QPainterPath()
        path.addRoundedRect(QRectF(margin, margin, w - 2 * margin, h - 2 * margin), radius, radius)
        p.fillPath(path, bg)

        # Texto
        p.setPen(QColor("#f0f0f0"))
        font = QFont()
        font.setPointSize(11)
        p.setFont(font)
        p.drawText(
            QRectF(16, 0, w * 0.55, h),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            self._label,
        )

        # Círculo deslizante
        track = w - 2 * margin - 2 * radius
        cx = margin + radius + track * self._offset
        cy = h / 2.0
        p.setBrush(QColor("#f5f5f5"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - radius + 2, cy - radius + 2, 2 * radius - 4, 2 * radius - 4))
