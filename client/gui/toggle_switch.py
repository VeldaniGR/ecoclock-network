"""Interruptor deslizante (pill + círculo) — recoloreado a paleta Eco'clock."""
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

    def text(self) -> str:
        """Devuelve el label del switch (para compatibilidad con tests)."""
        return self._label

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

        # Colores paleta Eco'clock
        # Off: --bar / --line (arena) | On: --leaf / --leaf2 (verde hoja)
        # Círculo: --field / --win (crema)
        if self._checked:
            bg_color = QColor("#6f9a4a")      # --leaf
            bg_color_end = QColor("#4f7a35")  # --leaf2
        else:
            bg_color = QColor("#ecdcba")      # --bar
            bg_color_end = QColor("#dcc79e")  # --line

        # Fondo píldora con gradiente sutil
        path = QPainterPath()
        path.addRoundedRect(QRectF(margin, margin, w - 2 * margin, h - 2 * margin), radius, radius)

        # Gradiente horizontal para el fondo
        from PyQt6.QtGui import QLinearGradient
        grad = QLinearGradient(margin, 0, w - margin, 0)
        grad.setColorAt(0, bg_color)
        grad.setColorAt(1, bg_color_end)
        p.fillPath(path, grad)

        # Texto label
        p.setPen(QColor("#3b2d1d"))  # --ink
        font = QFont()
        font.setPointSize(11)
        font.setWeight(QFont.Weight.Medium)
        p.setFont(font)
        p.drawText(
            QRectF(16, 0, w * 0.55, h),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            self._label,
        )

        # Círculo deslizante - crema (--field / --win)
        track = w - 2 * margin - 2 * radius
        cx = margin + radius + track * self._offset
        cy = h / 2.0
        circle_r = radius - 4

        # Sombra sutil del círculo
        p.setBrush(QColor(0, 0, 0, 30))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - circle_r + 1, cy - circle_r + 1, 2 * circle_r, 2 * circle_r))

        # Círculo principal
        p.setBrush(QColor("#fffaf0"))  # --field
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - circle_r, cy - circle_r, 2 * circle_r, 2 * circle_r))

        # Indicador interno (opcional: check cuando on)
        if self._checked:
            p.setBrush(QColor("#6f9a4a"))  # --leaf
            p.drawEllipse(QRectF(cx - 4, cy - 4, 8, 8))