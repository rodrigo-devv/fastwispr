from __future__ import annotations

# Lucide-style 24x24 stroke icons. Painted at 15px in 32px buttons. Footer actions stay 18px.

ICON_PX = 15
FOOTER_ICON_PX = 18
ICON_NAMES = (
    "sun",
    "moon",
    "minus",
    "x",
    "copy",
    "chevron-left",
    "chevron-right",
    "chevron-down",
    "clock",
    "search",
    "check",
    "settings",
    "book",
    "quote",
    "mic",
    "trash",
    "pencil",
    "more",
)


def icon_pixmap(name: str, color: str, *, size: int = ICON_PX, canvas: int | None = None):
    """Stroke-draw a Lucide icon. Import Qt only when called."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap

    if name not in ICON_NAMES:
        raise ValueError(f"Unknown icon: {name}")
    box = canvas or size
    pix = QPixmap(box, box)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.translate((box - size) / 2, (box - size) / 2)
    painter.scale(size / 24.0, size / 24.0)
    pen = QPen(QColor(color), 2.0)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    _stroke(painter, name)
    painter.end()
    return pix


def _stroke(painter, name: str) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPainterPath

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
    elif name == "chevron-down":
        painter.drawLine(6, 9, 12, 15)
        painter.drawLine(12, 15, 18, 9)
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
        body = QPainterPath()
        body.addEllipse(5, 3, 15, 18)
        hole = QPainterPath()
        hole.addEllipse(10, 1, 15, 16)
        painter.setBrush(painter.pen().color())
        painter.setPen(Qt.NoPen)
        painter.drawPath(body.subtracted(hole))
        painter.setBrush(Qt.NoBrush)
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
        painter.drawEllipse(7.5, 7.5, 9, 9)
        painter.drawEllipse(10.25, 10.25, 3.5, 3.5)
        for angle in range(0, 360, 60):
            painter.save()
            painter.translate(12, 12)
            painter.rotate(angle)
            painter.drawRect(-1.05, -11, 2.1, 3.4)
            painter.restore()
    elif name == "book":
        painter.drawRoundedRect(4, 3, 16, 18, 2, 2)
        painter.drawLine(12, 3, 12, 21)
        painter.drawLine(7, 8, 10, 8)
        painter.drawLine(14, 8, 17, 8)
    elif name == "quote":
        painter.drawRoundedRect(4, 6, 7, 8, 1.5, 1.5)
        painter.drawLine(4, 14, 4, 18)
        painter.drawLine(4, 18, 8, 14)
        painter.drawRoundedRect(13, 6, 7, 8, 1.5, 1.5)
        painter.drawLine(13, 14, 13, 18)
        painter.drawLine(13, 18, 17, 14)
    elif name == "mic":
        painter.drawRoundedRect(9, 3, 6, 11, 3, 3)
        painter.drawArc(7, 11, 10, 9, 0, -180 * 16)
        painter.drawLine(12, 20, 12, 22)
        painter.drawLine(9, 22, 15, 22)
    elif name == "trash":
        painter.drawLine(5, 7, 19, 7)
        painter.drawLine(9, 7, 9, 4)
        painter.drawLine(9, 4, 15, 4)
        painter.drawLine(15, 4, 15, 7)
        painter.drawRoundedRect(6, 7, 12, 13, 2, 2)
        painter.drawLine(10, 11, 10, 16)
        painter.drawLine(14, 11, 14, 16)
    elif name == "pencil":
        painter.drawLine(13, 5, 19, 11)
        painter.drawLine(19, 11, 8, 22)
        painter.drawLine(8, 22, 2, 22)
        painter.drawLine(2, 22, 2, 16)
        painter.drawLine(2, 16, 13, 5)
        painter.drawLine(11, 7, 17, 13)
    elif name == "more":
        painter.drawEllipse(4.5, 10.5, 3, 3)
        painter.drawEllipse(10.5, 10.5, 3, 3)
        painter.drawEllipse(16.5, 10.5, 3, 3)
