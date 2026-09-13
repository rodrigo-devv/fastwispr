from __future__ import annotations

from typing import Callable

from .theme import (
    OVERLAY_H,
    OVERLAY_MIN_W,
    OVERLAY_PAD_X,
    overlay_enter_pos,
    overlay_rest_pos,
    theme_tokens,
)

try:
    from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, Qt, QTimer, QParallelAnimationGroup
    from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
    from PySide6.QtWidgets import QApplication, QWidget
except ImportError as exc:  # pragma: no cover - optional extra
    raise RuntimeError("Install the GUI extra with: python -m pip install -e '.[gui]'") from exc


class QtRecordingOverlay(QWidget):
    """Frameless always-on-top pill. Duck-types the old Tk overlay API."""

    def __init__(self, *, theme_preference: str = "dark"):
        super().__init__(None)
        self.root = self
        self.theme_preference = theme_preference
        self.state = "idle"
        self.level = 0.0
        self.level_history: list[float] = []
        self.phase = 0
        self.elapsed_s = 0
        self._error_click: Callable[[], None] | None = None
        self._tokens = theme_tokens(theme_preference)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
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
        self.hide()

    def after(self, ms: int, callback) -> None:
        QTimer.singleShot(int(ms), callback)

    def run(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.exec()

    def set_error_handler(self, callback: Callable[[], None] | None) -> None:
        self._error_click = callback

    def set_theme_preference(self, preference: str) -> None:
        self.theme_preference = preference
        self._tokens = theme_tokens(preference)
        self.update()

    def set_level(self, level: float) -> None:
        self.level = max(0.0, min(1.0, float(level)))
        self.level_history = [*self.level_history, self.level][-24:]

    def hide_overlay(self) -> None:
        self._animate(show=False)

    def hide(self) -> None:  # noqa: A003 - matches Tk overlay
        super().hide()
        self.state = "idle"

    def set_state(self, state: str) -> None:
        mapped = "success" if state == "pasting" else state
        self.state = mapped
        if mapped == "recording":
            self.level = 0.0
            self.level_history = []
            self.phase = 0
            self.elapsed_s = 0
        if mapped == "idle":
            self.hide_overlay()
            return
        self._resize_for_state()
        self._animate(show=True)
        self.update()
        if mapped == "success":
            self.after(700, self.hide_overlay)
        elif mapped == "error":
            self.after(4000, self.hide_overlay)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self.state == "error" and self._error_click is not None:
            self._error_click()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        if self.state in {"idle"}:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        tokens = self._tokens
        path = QPainterPath()
        path.addRoundedRect(QRect(0, 0, self.width(), self.height()), 999, 999)
        painter.fillPath(path, QColor(tokens["surface"]))
        painter.setPen(QPen(QColor(tokens["border"]), 1))
        painter.drawPath(path)
        if self.state == "recording":
            self._paint_recording(painter, tokens)
        elif self.state == "processing":
            self._paint_processing(painter, tokens)
        elif self.state == "success":
            self._paint_text(painter, tokens["success"], "Done")
        else:
            self._paint_text(painter, tokens["error"], "Couldn't transcribe")
        painter.end()

    def _resize_for_state(self) -> None:
        width = 168 if self.state == "recording" else 196
        if self.state == "error":
            width = 210
        self.setFixedSize(width, OVERLAY_H)

    def _screen_metrics(self) -> tuple[int, int]:
        screen = self.screen() or QApplication.primaryScreen()
        geo = screen.geometry() if screen is not None else QRect(0, 0, 1280, 800)
        return geo.right(), geo.width()

    def _animate(self, *, show: bool) -> None:
        screen_right, screen_width = self._screen_metrics()
        rest_x, rest_y = overlay_rest_pos(screen_width, self.width())
        start_x, start_y = overlay_enter_pos(screen_right, self.width())
        if show:
            self.move(start_x, start_y)
            self.setWindowOpacity(0.0)
            super().show()
            end = QPoint(rest_x, rest_y)
            start = QPoint(start_x, start_y)
            duration = 220
            curve = QEasingCurve.OutCubic
        else:
            start = self.pos()
            end = QPoint(start_x, start_y)
            duration = 180
            curve = QEasingCurve.InCubic
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
            if self.phase % 30 == 0:
                self.elapsed_s += 1
        self.update()

    def _paint_recording(self, painter: QPainter, tokens: dict[str, str]) -> None:
        pulse = 0.55 + 0.45 * abs((self.phase % 30) / 15 - 1)
        painter.setBrush(QColor(tokens["accent"]))
        painter.setPen(Qt.NoPen)
        painter.setOpacity(pulse)
        painter.drawEllipse(OVERLAY_PAD_X, 15, 7, 7)
        painter.setOpacity(1.0)
        bars = self._bar_heights()
        x = OVERLAY_PAD_X + 16
        for height in bars:
            painter.setBrush(QColor(tokens["accent"]))
            painter.drawRoundedRect(x, 19 - height // 2, 2, max(3, height), 2, 2)
            x += 4
        painter.setPen(QColor(tokens["text_muted"]))
        painter.drawText(x + 8, 24, self._timer_text())

    def _timer_text(self) -> str:
        return f"{self.elapsed_s // 60:02d}:{self.elapsed_s % 60:02d}"

    def _paint_processing(self, painter: QPainter, tokens: dict[str, str]) -> None:
        painter.setPen(QPen(QColor(tokens["warning"]), 2))
        painter.setBrush(Qt.NoBrush)
        span = (self.phase * 12) % 360
        painter.drawArc(OVERLAY_PAD_X, 11, 16, 16, span * 16, 270 * 16)
        painter.setPen(QColor(tokens["text"]))
        painter.drawText(OVERLAY_PAD_X + 26, 24, "Transcribing…")

    def _paint_text(self, painter: QPainter, color: str, text: str) -> None:
        painter.setPen(QColor(color))
        painter.drawText(OVERLAY_PAD_X, 24, text)

    def _bar_heights(self) -> list[int]:
        count = 11
        if not self.level_history or max(self.level_history[-8:]) < 0.01:
            return [3 + (i + self.phase // 4) % 3 for i in range(count)]
        heights = []
        sample = self.level_history[-count:]
        sample = [0.0] * (count - len(sample)) + sample
        for level in sample:
            visible = min(1.0, level * 6) ** 0.55
            heights.append(int(3 + 14 * visible))
        return heights
