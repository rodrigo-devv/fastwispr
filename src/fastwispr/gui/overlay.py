from __future__ import annotations

import math
import time
from typing import Callable

from .theme import OVERLAY_H, OVERLAY_MIN_W, OVERLAY_PAD_X, overlay_enter_pos, overlay_rest_pos, theme_tokens

try:
    from PySide6.QtCore import QEasingCurve, QParallelAnimationGroup, QPoint, QPropertyAnimation, QRect, QRectF, Qt, QTimer
    from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QPainter, QPainterPath, QPen, QRegion
    from PySide6.QtWidgets import QApplication, QWidget
except ImportError as exc:  # pragma: no cover - optional extra
    raise RuntimeError("Install the GUI extra with: python -m pip install -e '.[gui]'") from exc


class QtRecordingOverlay(QWidget):
    """Signature pill: bottom-right, enters from the right, never steals focus."""

    def __init__(self, *, theme_preference: str = "dark"):
        super().__init__(None)
        self.root = self
        self.theme_preference = theme_preference
        self.state = "idle"
        self.level = 0.0
        self.level_history: list[float] = []
        self.phase = 0
        self._record_started = 0.0
        self._retry_rect = QRect()
        self._error_click: Callable[[], None] | None = None
        self._retry_click: Callable[[], None] | None = None
        self._tokens = theme_tokens(theme_preference)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        try:
            self.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)
        except Exception:
            pass
        self.setFixedHeight(OVERLAY_H)
        self.setMinimumWidth(OVERLAY_MIN_W)
        self._tick = QTimer(self)
        self._tick.timeout.connect(self._on_tick)
        self._tick.start(33)
        self._anim_group: QParallelAnimationGroup | None = None
        self._hide_gen = 0
        self.hide()

    def after(self, ms: int, callback) -> None:
        QTimer.singleShot(int(ms), callback)

    def run(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.exec()

    def set_error_handler(self, callback: Callable[[], None] | None) -> None:
        self._error_click = callback

    def set_retry_handler(self, callback: Callable[[], None] | None) -> None:
        self._retry_click = callback

    def set_theme_preference(self, preference: str) -> None:
        self.theme_preference = preference
        self._tokens = theme_tokens(preference)
        self.update()

    def set_level(self, level: float) -> None:
        self.level = max(0.0, min(1.0, float(level)))
        self.level_history = [*self.level_history, self.level][-24:]

    def hide_overlay(self) -> None:
        self._animate(show=False)

    def hide(self) -> None:  # noqa: A003
        super().hide()
        self.state = "idle"

    def set_state(self, state: str) -> None:
        mapped = "success" if state == "pasting" else state
        previous = self.state
        self.state = mapped
        if mapped == "recording" and previous != "recording":
            self.level = 0.0
            self.level_history = []
            self.phase = 0
            self._record_started = time.monotonic()
        if mapped == "idle":
            self.hide_overlay()
            return
        self._resize_for_state()
        self._apply_pill_mask()
        visible = self.isVisible() and self.windowOpacity() > 0.05
        if visible:
            rest = self._rest_point()
            self.move(rest)
        else:
            self._animate(show=True)
        self.update()
        self._hide_gen += 1
        token = self._hide_gen
        if mapped == "success":
            self.after(700, lambda t=token: self._auto_hide(t))
        elif mapped == "error":
            self.after(10_000, lambda t=token: self._auto_hide(t))

    def _auto_hide(self, token: int) -> None:
        if token == self._hide_gen and self.state in {"success", "error"}:
            self.hide_overlay()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self.state == "error" and self._retry_rect.contains(event.pos()):
            if self._retry_click is not None:
                self._retry_click()
            elif self._error_click is not None:
                self._error_click()
        elif self.state == "error" and self._error_click is not None:
            self._error_click()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        if self.state == "idle":
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        tokens = self._tokens
        path = QPainterPath()
        radius = (OVERLAY_H - 1) / 2
        path.addRoundedRect(QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0), radius, radius)
        painter.fillPath(path, QColor(tokens["surface"]))
        painter.setPen(QPen(QColor(tokens["border"]), 1))
        painter.drawPath(path)
        if self.state == "recording":
            self._paint_recording(painter, tokens)
        elif self.state == "processing":
            self._paint_processing(painter, tokens)
        elif self.state == "success":
            self._paint_success(painter, tokens)
        else:
            self._paint_error(painter, tokens)
        painter.end()

    def _resize_for_state(self) -> None:
        widths = {"recording": 228, "processing": 196, "success": 148, "error": 252}
        self.setFixedSize(widths.get(self.state, 168), OVERLAY_H)

    def _apply_pill_mask(self) -> None:
        path = QPainterPath()
        radius = OVERLAY_H / 2
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), radius, radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def _avail(self) -> QRect:
        screen = QGuiApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen is None:
            return QRect(0, 0, 1280, 800)
        return screen.availableGeometry()

    def _rest_point(self) -> QPoint:
        avail = self._avail()
        x, y = overlay_rest_pos(avail.right(), avail.bottom(), self.width(), self.height())
        return QPoint(x, y)

    def _enter_point(self) -> QPoint:
        avail = self._avail()
        x, y = overlay_enter_pos(avail.right(), avail.bottom(), self.width(), self.height())
        return QPoint(x, y)

    def _animate(self, *, show: bool) -> None:
        rest = self._rest_point()
        start_off = self._enter_point()
        if show:
            self.move(start_off)
            self.setWindowOpacity(0.0)
            super().show()
            start, end = start_off, rest
            duration = 220
            curve = QEasingCurve.OutCubic
        else:
            start, end = self.pos(), start_off
            duration = 180
            curve = QEasingCurve.InCubic
        if self._anim_group is not None:
            self._anim_group.stop()
        pos = QPropertyAnimation(self, b"pos", self)
        pos.setStartValue(start)
        pos.setEndValue(end)
        pos.setDuration(duration)
        pos.setEasingCurve(curve)
        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setStartValue(0.0 if show else 1.0)
        fade.setEndValue(1.0 if show else 0.0)
        fade.setDuration(duration)
        group = QParallelAnimationGroup(self)
        group.addAnimation(pos)
        group.addAnimation(fade)
        if not show:
            group.finished.connect(super().hide)
        self._anim_group = group
        group.start()

    def _on_tick(self) -> None:
        self.phase = (self.phase + 1) % 1000
        if self.state == "recording":
            self.level = max(0.0, self.level * 0.9)
            self.level_history = [*self.level_history, self.level][-24:]
        if self.state != "idle":
            self.update()

    def _elapsed_s(self) -> int:
        if not self._record_started:
            return 0
        return max(0, int(time.monotonic() - self._record_started))

    def _timer_text(self) -> str:
        elapsed = self._elapsed_s()
        return f"{elapsed // 60:02d}:{elapsed % 60:02d}"

    def _paint_recording(self, painter: QPainter, tokens: dict[str, str]) -> None:
        pulse = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(2 * math.pi * time.monotonic()))
        painter.setBrush(QColor(tokens["accent"]))
        painter.setPen(Qt.NoPen)
        painter.setOpacity(pulse)
        painter.drawEllipse(OVERLAY_PAD_X, 15, 7, 7)
        painter.setOpacity(1.0)
        x = OVERLAY_PAD_X + 16
        for height in self._bar_heights():
            painter.setBrush(QColor(tokens["accent"]))
            painter.drawRoundedRect(x, 19 - max(3, height) // 2, 2, max(3, height), 2, 2)
            x += 4
        painter.setPen(QColor(tokens["text_secondary"]))
        font = QFont("Cascadia Mono")
        if font.family() != "Cascadia Mono":
            font = QFont("Consolas")
        font.setPixelSize(11)
        painter.setFont(font)
        painter.drawText(QRect(self.width() - 13 - 40, 0, 40, OVERLAY_H), Qt.AlignVCenter | Qt.AlignRight, self._timer_text())

    def _paint_processing(self, painter: QPainter, tokens: dict[str, str]) -> None:
        painter.setPen(QPen(QColor(tokens["warning"]), 2))
        painter.setBrush(Qt.NoBrush)
        span = int((time.monotonic() * 360) % 360)
        painter.drawArc(OVERLAY_PAD_X, 11, 16, 16, span * 16, 270 * 16)
        painter.setPen(QColor(tokens["text"]))
        font = QFont("Segoe UI")
        font.setPixelSize(13)
        painter.setFont(font)
        painter.drawText(OVERLAY_PAD_X + 26, 0, 160, OVERLAY_H, Qt.AlignVCenter, "Transcribing...")

    def _paint_success(self, painter: QPainter, tokens: dict[str, str]) -> None:
        painter.setPen(QPen(QColor(tokens["success"]), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(OVERLAY_PAD_X + 2, 19, OVERLAY_PAD_X + 6, 24)
        painter.drawLine(OVERLAY_PAD_X + 6, 24, OVERLAY_PAD_X + 14, 13)
        painter.setPen(QColor(tokens["text"]))
        font = QFont("Segoe UI")
        font.setPixelSize(13)
        painter.setFont(font)
        painter.drawText(OVERLAY_PAD_X + 22, 0, 100, OVERLAY_H, Qt.AlignVCenter, "Done")

    def _paint_error(self, painter: QPainter, tokens: dict[str, str]) -> None:
        painter.setPen(QPen(QColor(tokens["error"]), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(OVERLAY_PAD_X, 11, 16, 16)
        painter.drawLine(OVERLAY_PAD_X + 8, 15, OVERLAY_PAD_X + 8, 21)
        painter.drawPoint(OVERLAY_PAD_X + 8, 24)
        painter.setPen(QColor(tokens["text"]))
        font = QFont("Segoe UI")
        font.setPixelSize(13)
        painter.setFont(font)
        painter.drawText(OVERLAY_PAD_X + 24, 0, 140, OVERLAY_H, Qt.AlignVCenter, "Couldn't transcribe")
        retry_font = QFont("Segoe UI")
        retry_font.setPixelSize(12)
        retry_font.setWeight(QFont.DemiBold)
        painter.setFont(retry_font)
        painter.setPen(QColor(tokens["accent"]))
        retry = QRect(self.width() - 62, 0, 50, OVERLAY_H)
        self._retry_rect = retry
        painter.drawText(retry, Qt.AlignVCenter | Qt.AlignRight, "Retry")

    def _bar_heights(self) -> list[int]:
        count = 11
        if not self.level_history or max(self.level_history[-8:]) < 0.01:
            return [3 + (i + self.phase // 4) % 3 for i in range(count)]
        sample = self.level_history[-count:]
        sample = [0.0] * (count - len(sample)) + sample
        heights = []
        for level in sample:
            visible = min(1.0, level * 6) ** 0.55
            heights.append(int(3 + 14 * visible))
        return heights
