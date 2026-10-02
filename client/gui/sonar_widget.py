"""Animación tipo sónar / radar (fondo mientras corre el auto) — recoloreado a paleta Eco'clock."""
from __future__ import annotations

import math

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class SonarWidget(QWidget):
    """
    Widget de animación tipo radar/sónar.
    Colores adaptados a la paleta Eco'clock:
    - Fondo: --bg / --bg2 (tierra oscura)
    - Anillos/pulso/barrido: tonos hoja/oro (--leaf, --acc)
    - Texto: --ink / --mute
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._angle = 0.0
        self._pulse = 0.0
        self._status = "En espera"
        self._detail = ""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setMinimumHeight(180)
        self.setProperty("class", "sonarWidget")

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

        # Fondo: tierra oscura (--bg / --bg2)
        p.fillRect(self.rect(), QColor("#1f1812"))

        # Anillos concéntricos - verde hoja con opacidad
        for i in range(1, 5):
            r = radius * i / 4
            # --leaf #6f9a4a con alpha variable
            alpha = 40 + i * 15
            pen = QPen(QColor(111, 154, 74, alpha))
            pen.setWidth(1)
            p.setPen(pen)
            p.drawEllipse(int(cx - r), int(cy - r), int(2 * r), int(2 * r))

        # Pulso expansivo - oro (--acc #c98a2b) con fade
        pr = radius * (0.2 + 0.8 * self._pulse)
        pulse_alpha = int(80 * (1 - self._pulse))
        pen = QPen(QColor(201, 138, 43, pulse_alpha))
        pen.setWidth(2)
        p.setPen(pen)
        p.drawEllipse(int(cx - pr), int(cy - pr), int(2 * pr), int(2 * pr))

        # Barrido rotatorio - verde hoja brillante
        rad = math.radians(self._angle)
        x2 = cx + radius * math.cos(rad)
        y2 = cy + radius * math.sin(rad)
        pen = QPen(QColor(111, 154, 74, 200))
        pen.setWidth(2)
        p.setPen(pen)
        p.drawLine(int(cx), int(cy), int(x2), int(y2))

        # Centro - verde hoja
        p.setBrush(QColor("#6f9a4a"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(int(cx - 4), int(cy - 4), 8, 8)

        # Texto - --ink / --mute
        p.setPen(QColor("#3b2d1d"))
        p.drawText(12, 20, self._status)
        if self._detail:
            p.setPen(QColor("#8a7556"))
            p.drawText(12, 38, self._detail[:80])