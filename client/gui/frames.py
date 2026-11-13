"""Carga de marcos (frames) del nodo desde assets locales."""
from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QWidget
from PyQt6.QtCore import QSize

FRAMES_DIR = Path(__file__).parent / "assets" / "frames"


def parse_unlocked_frames(raw: str | list | None) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x) for x in data if x]
    except Exception:
        pass
    return []


def frame_path(frame_id: str) -> Path | None:
    if not frame_id or frame_id == "none":
        return None
    p = FRAMES_DIR / f"{frame_id}.png"
    return p if p.exists() else None


def load_frame_pixmap(frame_id: str | None, size: int = 48) -> QPixmap:
    path = frame_path(frame_id or "")
    if path is None:
        return QPixmap()
    pix = QPixmap(str(path))
    if pix.isNull():
        return QPixmap()
    return pix.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

def make_logo_with_frame(
    logo_pix: QPixmap,
    frame_id: str | None,
    size: int = 64,
    parent: QWidget | None = None,
) -> QWidget:
    """Logo con marco superpuesto (frame encima del logo)."""
    box = QWidget(parent)
    box.setFixedSize(size, size)

    logo_lbl = QLabel(box)
    logo_lbl.setGeometry(4, 4, size - 8, size - 8)
    logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if not logo_pix.isNull():
        logo_lbl.setPixmap(
            logo_pix.scaled(
                size - 8,
                size - 8,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
    else:
        logo_lbl.setText("👥")
        logo_lbl.setStyleSheet("font-size: 22px;")

    frame_lbl = QLabel(box)
    frame_lbl.setGeometry(0, 0, size, size)
    frame_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    frame_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    fpix = load_frame_pixmap(frame_id, size)
    if not fpix.isNull():
        frame_lbl.setPixmap(fpix)
        frame_lbl.raise_()
    else:
        frame_lbl.hide()

    return box
