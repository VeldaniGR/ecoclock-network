"""Animación tipo sónar / radar (fondo mientras corre el auto)."""
from __future__ import annotations

import math

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class SonarWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._angle = 0.0
        self._pulse = 0.0
        self._status = "En espera"
        self._detail = ""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setMinimumHeight(180)

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start(33)  # ~30 fps

    def stop(self) -> None:
        self._timer.stop()
        self._status = "En espera"
        self.update()

    def set_status(self, status: str, detail: str = "") -> None:
        self._status = status
        self._detail = detail
        self.update()

    def _tick(self) -> None:
        self._angle = (self._angle + 3.5) % 360
        self._pulse = (self._pulse + 0.04) % 1.0
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        radius = min(w, h) * 0.42

        p.fillRect(self.rect(), QColor("#0d1210"))

        # Anillos
        for i in range(1, 5):
            r = radius * i / 4
            pen = QPen(QColor(40, 180, 120, 40 + i * 15))
            pen.setWidth(1)
            p.setPen(pen)
            p.drawEllipse(int(cx - r), int(cy - r), int(2 * r), int(2 * r))

        # Pulso
        pr = radius * (0.2 + 0.8 * self._pulse)
        pen = QPen(QColor(60, 220, 160, int(80 * (1 - self._pulse))))
        pen.setWidth(2)
        p.setPen(pen)
        p.drawEllipse(int(cx - pr), int(cy - pr), int(2 * pr), int(2 * pr))

        # Barrido
        rad = math.radians(self._angle)
        x2 = cx + radius * math.cos(rad)
        y2 = cy + radius * math.sin(rad)
        pen = QPen(QColor(100, 255, 180, 200))
        pen.setWidth(2)
        p.setPen(pen)
        p.drawLine(int(cx), int(cy), int(x2), int(y2))

        # Centro
        p.setBrush(QColor(80, 220, 160))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(cx - 4), int(cy - 4), 8, 8)

        # Texto
        p.setPen(QColor("#c8f0d8"))
        p.drawText(12, 20, self._status)
        if self._detail:
            p.setPen(QColor("#7aab90"))
            p.drawText(12, 38, self._detail[:80])
