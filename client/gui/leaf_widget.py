"""Hoja SVG animada (flotación + rotación suave), estilo propuesta HTML."""
from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, QSequentialAnimationGroup, Qt, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QWidget


class LeafWidget(QWidget):
    """
    Widget que dibuja una hoja SVG y la anima:
    - Flotación vertical: 0 → -10 → 0 en 6s ease-in-out (bucle suave sin saltos)
    - Rotación: 14° ↔ 4° ↔ 14° sincronizada con la flotación
    Respeta prefers-reduced-motion.
    """

    # SVG de la hoja (extraído del HTML, adaptado a viewBox 64x64)
    LEAF_SVG = (
        '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M8 54C6 28 24 8 56 8c0 30-16 48-40 46" fill="{leaf}"/>'
        '<path d="M8 54C22 38 34 26 52 12" stroke="{leaf2}" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
        '</svg>'
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._leaf_color = "#6f9a4a"
        self._leaf2_color = "#4f7a35"
        self._y_offset = 0.0
        self._rotation = 14.0
        self._animating = False
        self._reduced_motion = False

        # Renderer SVG
        self._renderer = QSvgRenderer()
        self._update_svg()

        # Tamaño fijo (64x64 en HTML)
        self.setFixedSize(64, 64)

        # Animaciones de flotación: 0 → -10 → 0 (ida y vuelta suave)
        self._float_up = QPropertyAnimation(self, b"yOffset")
        self._float_up.setDuration(3000)
        self._float_up.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._float_up.setStartValue(0.0)
        self._float_up.setEndValue(-10.0)

        self._float_down = QPropertyAnimation(self, b"yOffset")
        self._float_down.setDuration(3000)
        self._float_down.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._float_down.setStartValue(-10.0)
        self._float_down.setEndValue(0.0)

        # Grupo secuencial para flotación (ida + vuelta = bucle suave)
        self._float_group = QSequentialAnimationGroup(self)
        self._float_group.addAnimation(self._float_up)
        self._float_group.addAnimation(self._float_down)
        self._float_group.setLoopCount(-1)  # infinito

        # Animaciones de rotación: 14° → 4° → 14° (ida y vuelta suave)
        self._rot_down = QPropertyAnimation(self, b"rotation")
        self._rot_down.setDuration(3000)
        self._rot_down.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._rot_down.setStartValue(14.0)
        self._rot_down.setEndValue(4.0)

        self._rot_up = QPropertyAnimation(self, b"rotation")
        self._rot_up.setDuration(3000)
        self._rot_up.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._rot_up.setStartValue(4.0)
        self._rot_up.setEndValue(14.0)

        # Grupo secuencial para rotación (ida + vuelta = bucle suave)
        self._rot_group = QSequentialAnimationGroup(self)
        self._rot_group.addAnimation(self._rot_down)
        self._rot_group.addAnimation(self._rot_up)
        self._rot_group.setLoopCount(-1)  # infinito

        # Detectar prefers-reduced-motion
        self._check_reduced_motion()

    def _check_reduced_motion(self) -> None:
        """Verifica si el usuario prefiere movimiento reducido (accesibilidad)."""
        try:
            from PyQt6.QtGui import QGuiApplication
            hints = QGuiApplication.styleHints()
            if hasattr(hints, "prefersReducedMotion"):
                self._reduced_motion = hints.prefersReducedMotion()
        except Exception:
            pass

    def _update_svg(self) -> None:
        """Actualiza el SVG con los colores actuales."""
        svg_content = self.LEAF_SVG.format(
            leaf=self._leaf_color,
            leaf2=self._leaf2_color
        )
        self._renderer.load(svg_content.encode())
        self.update()

    def set_colors(self, leaf: str, leaf2: str) -> None:
        """Permite cambiar colores en runtime (ej. cambio de tema)."""
        self._leaf_color = leaf
        self._leaf2_color = leaf2
        self._update_svg()

    def start(self) -> None:
        """Inicia la animación."""
        if self._reduced_motion or self._animating:
            return
        self._float_group.start()
        self._rot_group.start()
        self._animating = True

    def stop(self) -> None:
        """Detiene la animación y resetea a estado base."""
        self._float_group.stop()
        self._rot_group.stop()
        self._y_offset = 0.0
        self._rotation = 14.0
        self._animating = False
        self.update()

    # ---- Properties para QPropertyAnimation (pyqtProperty) ----

    @pyqtProperty(float)
    def yOffset(self) -> float:
        return self._y_offset

    @yOffset.setter
    def yOffset(self, value: float) -> None:
        self._y_offset = value
        self.update()

    @pyqtProperty(float)
    def rotation(self) -> float:
        return self._rotation

    @rotation.setter
    def rotation(self, value: float) -> None:
        self._rotation = value
        self.update()

    # ---- Paint ----

    def paintEvent(self, _event) -> None:
        if not self._renderer.isValid():
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Centro del widget
        cx = self.width() / 2.0
        cy = self.height() / 2.0

        # Aplicar transformación: rotar alrededor del centro + traducir Y
        p.translate(cx, cy + self._y_offset)
        p.rotate(self._rotation)
        p.translate(-cx, -cy)

        # Renderizar SVG centrado
        # El SVG tiene viewBox 64x64, lo escalamos al widget
        self._renderer.render(p, QRectF(0, 0, self.width(), self.height()))