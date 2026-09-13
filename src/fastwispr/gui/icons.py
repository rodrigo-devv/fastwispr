from __future__ import annotations

# Lucide-style 24x24 stroke icons. Painted at 18px. No emoji.

ICON_PX = 18
ICON_NAMES = (
    "sun",
    "moon",
    "minus",
    "x",
    "copy",
    "chevron-left",
    "chevron-right",
    "clock",
    "search",
    "check",
    "settings",
    "mic",
)


def icon_pixmap(name: str, color: str, *, size: int = ICON_PX, canvas: int | None = None):
    """Stroke-draw a Lucide icon. Import Qt only when called."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPainter, QPen, QPixmap

    if name not in ICON_NAMES:
        raise ValueError(f"Unknown icon: {name}")
    box = canvas or size
    pix = QPixmap(box, box)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.translate((box - size) / 2, (box - size) / 2)
    painter.scale(size / 24.0, size / 24.0)
    pen = QPen(QColor(color), 2.4)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    _stroke(painter, name)
    painter.end()
    return pix


def _stroke(painter, name: str) -> None:
    if name == "x":
        painter.drawLine(18, 6, 6, 18)
        painter.drawLine(6, 6, 18, 18)
    elif name == "minus":
        painter.drawLine(5, 12, 19, 12)
    elif name == "chevron-left":
        painter.drawLine(15, 18, 9, 12)
        painter.drawLine(9, 12, 15, 6)
    elif name == "chevron-right":
        painter.drawLine(9, 18, 15, 12)
        painter.drawLine(15, 12, 9, 6)
    elif name == "copy":
        painter.drawRoundedRect(8, 8, 12, 12, 2, 2)
        painter.drawLine(8, 16, 6, 16)
        painter.drawLine(6, 16, 6, 6)
        painter.drawLine(6, 6, 16, 6)
        painter.drawLine(16, 6, 16, 8)
    elif name == "sun":
        painter.drawEllipse(8, 8, 8, 8)
        painter.drawLine(12, 2, 12, 4)
        painter.drawLine(12, 20, 12, 22)
        painter.drawLine(2, 12, 4, 12)
        painter.drawLine(20, 12, 22, 12)
        painter.drawLine(4.9, 4.9, 6.3, 6.3)
        painter.drawLine(17.7, 17.7, 19.1, 19.1)
        painter.drawLine(4.9, 19.1, 6.3, 17.7)
        painter.drawLine(17.7, 6.3, 19.1, 4.9)
    elif name == "moon":
        painter.drawArc(6, 4, 14, 16, 50 * 16, 260 * 16)
    elif name == "clock":
        painter.drawEllipse(3, 3, 18, 18)
        painter.drawLine(12, 7, 12, 12)
        painter.drawLine(12, 12, 16, 14)
    elif name == "search":
        painter.drawEllipse(4, 4, 12, 12)
        painter.drawLine(14.5, 14.5, 20, 20)
    elif name == "check":
        painter.drawLine(5, 12, 10, 17)
        painter.drawLine(10, 17, 19, 7)
    elif name == "settings":
        painter.drawEllipse(9, 9, 6, 6)
        for angle in (0, 45, 90, 135, 180, 225, 270, 315):
            painter.save()
            painter.translate(12, 12)
            painter.rotate(angle)
            painter.drawLine(0, -10, 0, -7)
            painter.restore()
    elif name == "mic":
        painter.drawRoundedRect(9, 3, 6, 11, 3, 3)
        painter.drawArc(7, 11, 10, 9, 0, -180 * 16)
        painter.drawLine(12, 20, 12, 22)
        painter.drawLine(9, 22, 15, 22)
