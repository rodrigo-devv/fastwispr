from __future__ import annotations

from pathlib import Path
from typing import Callable

from ..config import Config, load_config
from ..config_edit import set_config_value
from ..controller import DictationController
from ..db import DictationEvent, Store
from ..windows.settings_ui import apply_stt_preset_to_values, stt_preset_from_values
from .theme import (
    CHIP_H,
    COPY_BTN,
    FOOTER_H,
    HUB_DEFAULT,
    HUB_MAX,
    HUB_MIN,
    PAGEBAR_H,
    TITLEBAR_H,
    app_qss,
    format_clock,
    format_duration_ms,
    history_group_label,
    history_meta_line,
    hotkey_keycaps,
    hub_top_left,
    model_chip_label,
    preset_label,
    theme_tokens,
    resolve_theme_name,
)

try:
    from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QTimer
    from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QIcon, QPainter, QPainterPath, QPen, QPixmap, QRegion
    from .icons import ICON_PX, icon_pixmap
    from PySide6.QtWidgets import (
        QApplication,
        QButtonGroup,
        QDialog,
        QDialogButtonBox,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMenu,
        QMessageBox,
        QPlainTextEdit,
        QPushButton,
        QRadioButton,
        QScrollArea,
        QStackedWidget,
        QSystemTrayIcon,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - optional extra
    raise RuntimeError("Install the GUI extra with: python -m pip install -e '.[gui]'") from exc


PAGES = ("home", "history", "detail", "dictionary", "snippets", "settings", "speech", "privacy", "appearance", "about", "dictation", "shortcuts", "microphone", "general")


def _wipe_layout(layout) -> None:
    """Recursively remove nested widgets. takeAt(widget-only) left duplicates on Home."""
    if layout is None:
        return
    while layout.count():
        item = layout.takeAt(0)
        child = item.widget()
        nested = item.layout()
        if child is not None:
            child.setParent(None)
            child.deleteLater()
        if nested is not None:
            _wipe_layout(nested)


def tray_icon_pixmap() -> QPixmap:
    pix = QPixmap(16, 16)
    pix.fill(QColor("#090A0B"))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#E10600"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(4, 4, 8, 8)
    painter.end()
    return pix


class TitleBar(QWidget):
    def __init__(self, on_theme, on_min, on_close, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(TITLEBAR_H)
        self._drag: QPoint | None = None
        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("IconBtn")
        self.theme_btn.setFixedSize(32, 32)
        self.theme_btn.setToolTip("Theme")
        self.theme_btn.clicked.connect(on_theme)
        self.minimize_btn = QPushButton()
        self.minimize_btn.setObjectName("CaptionBtn")
        self.minimize_btn.setToolTip("Minimize")
        self.minimize_btn.clicked.connect(on_min)
        self.close_btn = QPushButton()
        self.close_btn.setObjectName("CaptionClose")
        self.close_btn.setToolTip("Close")
        self.close_btn.clicked.connect(on_close)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 0, 0)
        layout.setSpacing(0)
        brand = QFont("Segoe UI")
        brand.setPixelSize(14)
        brand.setWeight(QFont.DemiBold)
        brand.setLetterSpacing(QFont.PercentageSpacing, 98)
        fast = QLabel("Fast")
        fast.setObjectName("WordmarkFast")
        fast.setFont(brand)
        wispr = QLabel("WISPR")
        wispr.setObjectName("WordmarkWispr")
        wispr.setFont(brand)
        layout.addWidget(fast)
        layout.addWidget(wispr)
        layout.addStretch(1)
        layout.addWidget(self.theme_btn)
        spacer = QWidget()
        spacer.setFixedWidth(8)
        layout.addWidget(spacer)
        divider = QFrame()
        divider.setObjectName("ChromeDivider")
        divider.setFixedSize(1, 16)
        layout.addWidget(divider)
        layout.addWidget(self.minimize_btn)
        layout.addWidget(self.close_btn)

    def recolor(self, tokens: dict[str, str], resolved_theme: str) -> None:
        # Dark UI shows a sun (switch to light); light UI shows a moon.
        theme_icon = "sun" if resolved_theme == "dark" else "moon"
        self.theme_btn.setIcon(QIcon(icon_pixmap(theme_icon, tokens["text_secondary"], size=ICON_PX, canvas=32)))
        self.theme_btn.setIconSize(QSize(ICON_PX, ICON_PX))
        self.minimize_btn.setIcon(QIcon(icon_pixmap("minus", tokens["text_secondary"], size=ICON_PX, canvas=40)))
        self.minimize_btn.setIconSize(QSize(ICON_PX, ICON_PX))
        self.close_btn.setIcon(QIcon(icon_pixmap("x", tokens["accent"], size=ICON_PX, canvas=40)))
        self.close_btn.setIconSize(QSize(ICON_PX, ICON_PX))

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        del event  # Do not maximize.


class PageBar(QWidget):
    def __init__(self, title: str, on_back, on_add=None, tokens: dict[str, str] | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("PageBar")
        self.setFixedHeight(PAGEBAR_H)
        palette = tokens or theme_tokens("dark")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        back = QPushButton()
        back.setObjectName("IconBtn")
        back.setFixedSize(32, 32)
        back.setToolTip("Back")
        back.setIcon(QIcon(icon_pixmap("chevron-left", palette["text_secondary"], size=ICON_PX, canvas=32)))
        back.setIconSize(QSize(ICON_PX, ICON_PX))
        back.clicked.connect(on_back)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size:14px; font-weight:600;")
        layout.addWidget(back)
        layout.addWidget(title_lbl)
        layout.addStretch(1)
        if on_add is not None:
            add = QPushButton("Add")
            add.setObjectName("Primary")
            add.clicked.connect(on_add)
            layout.addWidget(add)


class Keycap(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Keycap")
        self.setFixedHeight(20)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        label = QLabel(text)
        label.setStyleSheet("font-size:11px; font-family: 'Cascadia Mono', Consolas, monospace;")
        layout.addWidget(label)


class StatusDot(QWidget):
    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(6, 6)

    def set_color(self, color: str) -> None:
        self._color = color
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self._color))
        painter.drawEllipse(0, 0, 6, 6)
        painter.end()


class TranscriptRow(QFrame):
    def __init__(self, event: DictationEvent, on_copy, on_open, tokens: dict[str, str] | None = None, parent=None):
        super().__init__(parent)
        palette = tokens or theme_tokens("dark")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        col = QVBoxLayout()
        text = QLabel(event.final_text.replace("\n", " ")[:90] or "Transcription failed")
        text.setWordWrap(True)
        meta = QLabel(history_meta_line(event.created_at, event.audio_duration_ms))
        meta.setObjectName("Meta")
        col.addWidget(text)
        col.addWidget(meta)
        layout.addLayout(col, 1)
        copy_btn = QPushButton()
        copy_btn.setObjectName("CopyBtn")
        copy_btn.setFixedSize(COPY_BTN, COPY_BTN)
        copy_btn.setToolTip("Copy")
        copy_btn.setIcon(QIcon(icon_pixmap("copy", palette["text_secondary"], size=ICON_PX, canvas=28)))
        copy_btn.setIconSize(QSize(ICON_PX, ICON_PX))
        copy_btn.clicked.connect(lambda: on_copy(event.final_text))
        layout.addWidget(copy_btn, 0, Qt.AlignTop)
        self.mousePressEvent = lambda ev: on_open(event) if ev.button() == Qt.LeftButton else None  # type: ignore[method-assign]


class Toast(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(* (280, 40))
        layout = QHBoxLayout(self)
        self.label = QLabel("Copied")
        layout.addWidget(self.label)
        self._hide = QTimer(self)
        self._hide.setSingleShot(True)
        self._hide.timeout.connect(self.hide)

    def show_message(self, text: str, anchor: QWidget) -> None:
        self.label.setText(text)
        geo = anchor.frameGeometry()
        self.move(geo.right() - self.width() - 12, geo.bottom() - self.height() - 12)
        self.show()
        self._hide.start(1400)


class PasteFailedCard(QWidget):
    def __init__(self, on_copy, on_retry, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        box = QVBoxLayout(self)
        title = QLabel("Paste failed")
        title.setStyleSheet("font-weight:600;")
        box.addWidget(title)
        box.addWidget(QLabel("Your transcript is safe."))
        row = QHBoxLayout()
        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("Primary")
        copy_btn.clicked.connect(lambda: (on_copy(), self.hide()))
        retry = QPushButton("Retry")
        retry.clicked.connect(lambda: (on_retry(), self.hide()))
        row.addWidget(copy_btn)
        row.addWidget(retry)
        box.addLayout(row)


class AppShell(QWidget):
    def __init__(
        self,
        config: Config,
        store: Store,
        config_path: Path,
        controller: DictationController | None = None,
        overlay=None,
        parent=None,
    ):
        super().__init__(parent)
        self.config = config
        self.store = store
        self.config_path = config_path
        self.controller = controller
        self.overlay = overlay
        self.theme_preference = config.ui_theme
        self._tokens = theme_tokens(config.ui_theme)
        self._page = "home"
        self._ready = False
        self.status = "Ready"
        self._detail: DictationEvent | None = None
        self.setObjectName("AppShell")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setMinimumSize(*HUB_MIN)
        self.setMaximumSize(*HUB_MAX)
        self.resize(*HUB_DEFAULT)
        root = QVBoxLayout(self)
        root.setContentsMargins(1, 1, 1, 1)
        root.setSpacing(0)
        self.titlebar = TitleBar(self._cycle_theme, self.showMinimized, self.confirm_close)
        root.addWidget(self.titlebar)
        self.header_line = QFrame()
        self.header_line.setObjectName("SectionDivider")
        self.header_line.setFixedHeight(1)
        root.addWidget(self.header_line)
        self.page_bar_host = QWidget()
        self.page_bar_layout = QVBoxLayout(self.page_bar_host)
        self.page_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.page_bar_layout.setSpacing(0)
        root.addWidget(self.page_bar_host)
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.pages = {name: QWidget() for name in PAGES}
        for widget in self.pages.values():
            self.stack.addWidget(widget)
        self.toast = Toast()
        self.paste_card = PasteFailedCard(self.copy_last, self.retry_last)
        self.apply_theme()
        self._ready = True
        self.show_page("home")

    def place_on_tray_screen(self) -> None:
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen is not None else self.geometry()
        x, y = hub_top_left(avail.right(), avail.bottom(), self.width(), self.height())
        self.move(x, y)

    def apply_theme(self) -> None:
        system_dark = True
        hints = QGuiApplication.styleHints()
        if hints is not None:
            try:
                system_dark = hints.colorScheme() == Qt.ColorScheme.Dark
            except Exception:
                system_dark = True
        tokens = theme_tokens(self.theme_preference, system_dark)
        self._tokens = tokens
        self.setStyleSheet(app_qss(tokens))
        resolved = resolve_theme_name(self.theme_preference, system_dark)
        self.titlebar.recolor(tokens, resolved)
        if self.overlay is not None and hasattr(self.overlay, "set_theme_preference"):
            self.overlay.set_theme_preference(self.theme_preference)
        if self._ready:
            self.show_page(self._page, self._detail)

    def _cycle_theme(self) -> None:
        order = ["dark", "light", "system"]
        idx = order.index(self.theme_preference) if self.theme_preference in order else 0
        self.set_theme(order[(idx + 1) % len(order)])

    def set_theme(self, name: str) -> None:
        self.theme_preference = name
        set_config_value(self.config_path, "ui.theme", name)
        self.config = load_config(self.config_path)
        self.apply_theme()

    def show_page(self, name: str, event: DictationEvent | None = None) -> None:
        self._detail = event
        self._page = name
        builders = {
            "home": self._build_home,
            "history": self._build_history,
            "detail": self._build_detail,
            "dictionary": self._build_dictionary,
            "snippets": self._build_snippets,
            "settings": self._build_settings,
            "speech": self._build_speech,
            "privacy": self._build_privacy,
            "appearance": self._build_appearance,
            "about": self._build_about,
            "dictation": lambda: self._build_simple("dictation", [("dictation.min_record_seconds", "Minimum seconds"), ("dictation.min_audio_rms", "Minimum RMS"), ("injection.restore_clipboard", "Restore clipboard")]),
            "shortcuts": lambda: self._fill_info("shortcuts", [f"Dictate  {self.config.hotkey}", "Copy last  Shift+Alt+Z"]),
            "microphone": lambda: self._fill_info("microphone", ["Input device  Default"]),
            "general": lambda: self._build_simple("general", [("activation.trigger", "Trigger"), ("activation.mode", "Mode")]),
        }
        widget = self.pages[name]
        _wipe_layout(widget.layout())
        builders[name]()
        _wipe_layout(self.page_bar_layout)
        if name != "home":
            titles = {
                "history": "History",
                "detail": "Transcript",
                "dictionary": "Dictionary",
                "snippets": "Snippets",
                "settings": "Settings",
                "speech": "Speech recognition",
                "privacy": "Privacy",
                "appearance": "Appearance",
                "about": "About",
                "dictation": "Dictation",
                "shortcuts": "Shortcuts",
                "microphone": "Microphone",
                "general": "General",
            }
            add = None
            if name == "dictionary":
                add = self._add_dictionary
            elif name == "snippets":
                add = self._add_snippet
            back_to = "history" if name == "detail" else "settings" if name not in {"history", "dictionary", "snippets", "settings"} else "home"
            if name in {"history", "dictionary", "snippets", "settings"}:
                back_to = "home"
            self.page_bar_layout.addWidget(PageBar(titles[name], lambda: self.show_page(back_to), add, tokens=self._tokens))
            self.page_bar_host.show()
        else:
            self.page_bar_host.hide()
        self.stack.setCurrentWidget(widget)

    def open_hub(self) -> None:
        self.place_on_tray_screen()
        self.show()
        self.raise_()
        self.activateWindow()

    def set_status(self, text: str) -> None:
        self.status = text
        if self.stack.currentWidget() is self.pages["home"]:
            self.show_page("home")

    def copy_text(self, text: str) -> None:
        if not text:
            return
        if self.controller is not None:
            copy = getattr(self.controller.injector, "copy_text", None)
            if callable(copy):
                copy(text)
            else:
                QApplication.clipboard().setText(text)
        else:
            QApplication.clipboard().setText(text)
        self.toast.show_message("Copied", self)

    def copy_last(self) -> None:
        text = self.controller.copy_last_transcript() if self.controller is not None else ""
        if not text:
            event = self.store.latest_completed_event()
            text = event.final_text if event else ""
            if text:
                self.copy_text(text)
            return
        self.toast.show_message("Copied", self)

    def retry_last(self) -> None:
        if self.controller is not None:
            self.controller.retry_paste()

    def show_paste_failed(self) -> None:
        self.place_on_tray_screen()
        geo = self.frameGeometry()
        self.paste_card.move(geo.right() - 240, geo.bottom() - 140)
        self.paste_card.show()

    def confirm_close(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("FastWISPR")
        box.setText("Close FastWISPR?")
        box.setInformativeText("Minimize keeps dictation on the taskbar. Quit stops the app.")
        minimize = box.addButton("Minimize to taskbar", QMessageBox.ButtonRole.AcceptRole)
        quit_btn = box.addButton("Quit", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked is minimize:
            self.showMinimized()
        elif clicked is quit_btn:
            QApplication.quit()

    def closeEvent(self, event) -> None:  # noqa: N802
        event.ignore()
        self.confirm_close()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 9, 9)
        painter.fillPath(path, QColor(self._tokens["bg"]))
        painter.setPen(QPen(QColor(self._tokens["border"]), 1))
        painter.drawPath(path)
        painter.end()

    def resizeEvent(self, event) -> None:  # noqa: N802
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 9, 9)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))
        super().resizeEvent(event)

    def _section_line(self) -> QFrame:
        line = QFrame()
        line.setObjectName("SectionDivider")
        line.setFixedHeight(1)
        return line

    def _clear(self, name: str) -> QVBoxLayout:
        widget = self.pages[name]
        layout = widget.layout()
        if layout is None:
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(16, 12, 16, 16)
            layout.setSpacing(12)
        else:
            _wipe_layout(layout)
        return layout

    def _build_home(self) -> None:
        layout = self._clear("home")
        layout.addStretch(1)
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_row.addStretch(1)
        color = {"Ready": self._tokens["text_muted"], "Recording": self._tokens["accent"], "Processing": self._tokens["warning"], "Error": self._tokens["error"]}.get(self.status, self._tokens["text_muted"])
        status_row.addWidget(StatusDot(color), 0, Qt.AlignVCenter)
        label = QLabel(self.status)
        label.setObjectName("StatusLabel")
        status_row.addWidget(label)
        status_row.addStretch(1)
        layout.addLayout(status_row)
        hint = QHBoxLayout()
        hint.addStretch(1)
        hold = QLabel("Hold")
        hold.setObjectName("Hint")
        hint.addWidget(hold)
        for cap in hotkey_keycaps(self.config.hotkey):
            hint.addWidget(Keycap(cap))
        rest = QLabel("to dictate")
        rest.setObjectName("Hint")
        hint.addWidget(rest)
        hint.addStretch(1)
        layout.addLayout(hint)
        chips = QHBoxLayout()
        chips.setSpacing(8)
        chips.addWidget(self._chip("Model", model_chip_label(self.config.stt_model), lambda: self.show_page("speech")), 1)
        chips.addWidget(self._chip("Microphone", "Default", lambda: self.show_page("microphone")), 1)
        layout.addLayout(chips)
        layout.addWidget(self._section_line())
        recent_head = QHBoxLayout()
        recent_lbl = QLabel("Recent")
        recent_lbl.setStyleSheet("font-size:14px; font-weight:600;")
        view_all = QPushButton("View all")
        view_all.setObjectName("Ghost")
        view_all.clicked.connect(lambda: self.show_page("history"))
        recent_head.addWidget(recent_lbl)
        recent_head.addStretch(1)
        recent_head.addWidget(view_all)
        layout.addLayout(recent_head)
        events = self.store.recent_dictation_events(limit=3, transcripts_only=True)
        if not events:
            empty = QLabel("No transcriptions yet")
            empty.setObjectName("Secondary")
            layout.addWidget(empty)
        for event in events:
            layout.addWidget(TranscriptRow(event, self.copy_text, lambda ev: self.show_page("detail", ev), tokens=self._tokens))
        layout.addStretch(1)
        layout.addWidget(self._section_line())
        footer = QHBoxLayout()
        history = QPushButton(" History")
        history.setFixedHeight(FOOTER_H)
        history.setIcon(QIcon(icon_pixmap("clock", self._tokens["text_secondary"], canvas=FOOTER_H)))
        history.setIconSize(QSize(ICON_PX, ICON_PX))
        history.clicked.connect(lambda: self.show_page("history"))
        settings = QPushButton(" Settings")
        settings.setObjectName("Primary")
        settings.setFixedHeight(FOOTER_H)
        settings.setIcon(QIcon(icon_pixmap("settings", "#FFFFFF", canvas=FOOTER_H)))
        settings.setIconSize(QSize(ICON_PX, ICON_PX))
        settings.clicked.connect(lambda: self.show_page("settings"))
        footer.addWidget(history)
        footer.addWidget(settings)
        layout.addLayout(footer)

    def _chip(self, caption: str, value: str, on_click) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Chip")
        frame.setFixedHeight(CHIP_H)
        frame.setCursor(Qt.PointingHandCursor)
        row = QHBoxLayout(frame)
        row.setContentsMargins(12, 6, 10, 6)
        col = QVBoxLayout()
        col.setSpacing(0)
        cap = QLabel(caption)
        cap.setObjectName("Meta")
        val = QLabel(value)
        col.addWidget(cap)
        col.addWidget(val)
        row.addLayout(col, 1)
        chev = QLabel()
        chev.setPixmap(icon_pixmap("chevron-right", self._tokens["text_muted"], canvas=ICON_PX))
        row.addWidget(chev)
        frame.mousePressEvent = lambda ev, cb=on_click: cb() if ev.button() == Qt.LeftButton else None  # type: ignore[method-assign]
        return frame

    def _build_history(self) -> None:
        layout = self._clear("history")
        search = QLineEdit()
        search.setPlaceholderText("Search")
        search.setFixedHeight(34)
        layout.addWidget(search)
        host = QVBoxLayout()
        scroll_wrap = QWidget()
        scroll_wrap.setLayout(host)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_wrap)
        layout.addWidget(scroll, 1)

        def refresh(text: str = "") -> None:
            while host.count():
                item = host.takeAt(0)
                child = item.widget()
                if child is not None:
                    child.deleteLater()
            events = self.store.recent_dictation_events(limit=80, query=text.strip() or None)
            grouped: dict[str, list[DictationEvent]] = {}
            for event in events:
                grouped.setdefault(history_group_label(event.created_at), []).append(event)
            if not events:
                empty_wrap = QVBoxLayout()
                clock = QLabel()
                clock.setPixmap(icon_pixmap("clock", self._tokens["text_muted"], size=22, canvas=22))
                clock.setAlignment(Qt.AlignCenter)
                empty = QLabel("No transcriptions yet")
                empty.setObjectName("Secondary")
                empty.setAlignment(Qt.AlignCenter)
                hint = QLabel("Hold Ctrl+Space and start speaking.")
                hint.setObjectName("Secondary")
                hint.setAlignment(Qt.AlignCenter)
                empty_wrap.addWidget(clock)
                empty_wrap.addWidget(empty)
                empty_wrap.addWidget(hint)
                box = QWidget()
                box.setLayout(empty_wrap)
                host.addWidget(box)
                return
            for group, rows in grouped.items():
                header = QLabel(group)
                header.setStyleSheet("font-size:14px; font-weight:600;")
                host.addWidget(header)
                for event in rows:
                    host.addWidget(TranscriptRow(event, self.copy_text, lambda ev: self.show_page("detail", ev), tokens=self._tokens))

        search.textChanged.connect(refresh)
        refresh()

    def _build_detail(self) -> None:
        layout = self._clear("detail")
        event = self._detail
        if event is None:
            layout.addWidget(QLabel("No transcript selected."))
            return
        panel = QFrame()
        panel.setObjectName("TranscriptPanel")
        panel_l = QVBoxLayout(panel)
        body = QLabel(event.final_text or "Transcription failed")
        body.setWordWrap(True)
        body.setStyleSheet("font-size:13px;")
        panel_l.addWidget(body)
        layout.addWidget(panel)
        layout.addWidget(QLabel(f"When\n{event.created_at}"))
        layout.addWidget(QLabel(f"Duration\n{format_duration_ms(event.audio_duration_ms)}"))
        layout.addWidget(QLabel(f"Model\n{preset_label(event.stt_model or self.config.stt_model)} · {model_chip_label(event.stt_model or self.config.stt_model)}"))
        layout.addStretch(1)
        row = QHBoxLayout()
        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("Primary")
        copy_btn.clicked.connect(lambda: self.copy_text(event.final_text))
        edit = QPushButton("Edit")
        edit.clicked.connect(lambda: self._edit_event(event))
        retry = QPushButton("Retry")
        retry.clicked.connect(lambda: self.controller.retry_paste(event.final_text) if self.controller else None)
        row.addWidget(copy_btn)
        row.addWidget(edit)
        row.addWidget(retry)
        layout.addLayout(row)

    def _edit_event(self, event: DictationEvent) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit transcript")
        box = QVBoxLayout(dialog)
        editor = QPlainTextEdit(event.final_text)
        box.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() == QDialog.Accepted:
            self.store.update_dictation_text(event.id, editor.toPlainText())
            updated = self.store.get_dictation_event(event.id)
            self.show_page("detail", updated)

    def _build_dictionary(self) -> None:
        layout = self._clear("dictionary")
        search = QLineEdit()
        search.setPlaceholderText("Search")
        layout.addWidget(search)
        host = QVBoxLayout()
        wrap = QWidget()
        wrap.setLayout(host)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(wrap)
        layout.addWidget(scroll, 1)

        def refresh(text: str = "") -> None:
            while host.count():
                item = host.takeAt(0)
                child = item.widget()
                if child is not None:
                    child.deleteLater()
            needle = text.strip().lower()
            for entry in self.store.dictionary_entries():
                if needle and needle not in entry.term.lower() and needle not in entry.replacement.lower():
                    continue
                row = QHBoxLayout()
                row.addWidget(QLabel(f"{entry.term}  →  {entry.replacement}"), 1)
                delete = QPushButton("Delete")
                delete.setObjectName("Ghost")
                delete.clicked.connect(lambda _=False, term=entry.term: (self.store.delete_dictionary(term), refresh(search.text())))
                row.addWidget(delete)
                frame = QWidget()
                frame.setLayout(row)
                host.addWidget(frame)

        search.textChanged.connect(refresh)
        refresh()

    def _add_dictionary(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Add word")
        box = QVBoxLayout(dialog)
        spoken = QLineEdit()
        spoken.setPlaceholderText("Spoken")
        written = QLineEdit()
        written.setPlaceholderText("Written")
        box.addWidget(spoken)
        box.addWidget(written)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() == QDialog.Accepted and spoken.text().strip():
            self.store.upsert_dictionary(spoken.text(), written.text() or spoken.text())
            self.show_page("dictionary")

    def _build_snippets(self) -> None:
        layout = self._clear("snippets")
        for snippet in self.store.list_snippets():
            row = QHBoxLayout()
            col = QVBoxLayout()
            col.addWidget(QLabel(snippet.cue))
            preview = QLabel(snippet.body.splitlines()[0][:48] if snippet.body else "")
            preview.setObjectName("Secondary")
            col.addWidget(preview)
            row.addLayout(col, 1)
            edit = QPushButton("Edit")
            edit.clicked.connect(lambda _=False, sn=snippet: self._edit_snippet(sn.cue, sn.body))
            delete = QPushButton("Delete")
            delete.clicked.connect(lambda _=False, cue=snippet.cue: (self.store.delete_snippet(cue), self.show_page("snippets")))
            row.addWidget(edit)
            row.addWidget(delete)
            frame = QWidget()
            frame.setLayout(row)
            layout.addWidget(frame)
        layout.addStretch(1)

    def _add_snippet(self) -> None:
        self._edit_snippet("", "")

    def _edit_snippet(self, cue: str, body: str) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Snippet")
        box = QVBoxLayout(dialog)
        trigger = QLineEdit(cue)
        trigger.setPlaceholderText("Trigger phrase")
        editor = QPlainTextEdit(body)
        box.addWidget(trigger)
        box.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() == QDialog.Accepted and trigger.text().strip():
            if cue and cue != trigger.text().strip():
                self.store.delete_snippet(cue)
            self.store.upsert_snippet(trigger.text(), editor.toPlainText())
            self.show_page("snippets")

    def _build_settings(self) -> None:
        layout = self._clear("settings")
        rows = [
            ("General", "general"),
            ("Dictation", "dictation"),
            ("Microphone", "microphone"),
            ("Speech recognition", "speech"),
            ("Privacy", "privacy"),
            ("Shortcuts", "shortcuts"),
            ("Appearance", "appearance"),
            ("About", "about"),
        ]
        for label, page in rows:
            btn = QPushButton(label)
            btn.setIcon(QIcon(icon_pixmap("chevron-right", self._tokens["text_muted"], canvas=ICON_PX)))
            btn.setIconSize(QSize(ICON_PX, ICON_PX))
            btn.setLayoutDirection(Qt.RightToLeft)
            btn.setFixedHeight(46)
            btn.clicked.connect(lambda _=False, p=page: self.show_page(p))
            layout.addWidget(btn)
        layout.addStretch(1)

    def _build_speech(self) -> None:
        layout = self._clear("speech")
        layout.addWidget(QLabel("Preset"))
        row = QHBoxLayout()
        group = QButtonGroup(self.pages["speech"])
        current = stt_preset_from_values(
            {
                "stt.model": self.config.stt_model,
                "stt.device": self.config.stt_device,
                "stt.compute_type": self.config.stt_compute_type,
            }
        )
        for name in ("Fast", "Balanced", "Accurate"):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setChecked(current == name)
            if current == name:
                btn.setObjectName("Primary")
            btn.clicked.connect(lambda _=False, n=name: self._apply_preset(n))
            group.addButton(btn)
            row.addWidget(btn)
        layout.addLayout(row)
        for key, value in (
            ("Model", model_chip_label(self.config.stt_model)),
            ("Language", self.config.stt_language),
            ("Device", self.config.stt_device),
            ("Compute", self.config.stt_compute_type),
        ):
            layout.addWidget(QLabel(f"{key}\n{value}"))
        caption = QLabel("Local faster-whisper. First run may download the model if it is not cached. No audio leaves the machine.")
        caption.setObjectName("Secondary")
        caption.setWordWrap(True)
        layout.addWidget(caption)
        layout.addStretch(1)

    def _apply_preset(self, name: str) -> None:
        values = apply_stt_preset_to_values(
            {
                "stt.model": self.config.stt_model,
                "stt.device": self.config.stt_device,
                "stt.compute_type": self.config.stt_compute_type,
            },
            name,
        )
        for key in ("stt.model", "stt.device", "stt.compute_type"):
            set_config_value(self.config_path, key, values[key])
        self.config = load_config(self.config_path)
        self.show_page("speech")

    def _build_privacy(self) -> None:
        layout = self._clear("privacy")
        facts = [
            f"Audio retention  {'On' if self.config.store_audio else 'Off (default)'}",
            f"Raw transcripts  {'On' if self.config.store_raw_transcripts else 'Off (default)'}",
            "Processing  Local",
            "Cloud processing  Not available",
        ]
        for line in facts:
            layout.addWidget(QLabel(line))
        layout.addStretch(1)

    def _build_appearance(self) -> None:
        layout = self._clear("appearance")
        for name in ("dark", "light", "system"):
            radio = QRadioButton(name.capitalize())
            radio.setChecked(self.theme_preference == name)
            radio.toggled.connect(lambda checked, n=name: self.set_theme(n) if checked else None)
            layout.addWidget(radio)
        layout.addStretch(1)

    def _build_about(self) -> None:
        self._fill_info("about", ["FastWISPR 0.1.0", "Local-first dictation for Windows.", "MIT License"])

    def _fill_info(self, page: str, lines: list[str]) -> None:
        layout = self._clear(page)
        for line in lines:
            layout.addWidget(QLabel(line))
        layout.addStretch(1)

    def _build_simple(self, page: str, fields: list[tuple[str, str]]) -> None:
        layout = self._clear(page)
        values = {
            "dictation.min_record_seconds": f"{self.config.min_record_seconds:g}",
            "dictation.min_audio_rms": f"{self.config.min_audio_rms:g}",
            "injection.restore_clipboard": "true" if self.config.restore_clipboard else "false",
            "activation.trigger": self.config.activation_trigger,
            "activation.mode": self.config.activation_mode,
        }
        editors: dict[str, QLineEdit] = {}
        for key, label in fields:
            layout.addWidget(QLabel(label))
            editor = QLineEdit(values[key])
            editors[key] = editor
            layout.addWidget(editor)
        save = QPushButton("Save")
        save.setObjectName("Primary")

        def persist() -> None:
            for key, editor in editors.items():
                set_config_value(self.config_path, key, editor.text().strip())
            self.config = load_config(self.config_path)
            self.toast.show_message("Saved", self)

        save.clicked.connect(persist)
        layout.addWidget(save)
        layout.addStretch(1)


def attach_tray(hub: AppShell, *, on_start: Callable[[], None], on_pause: Callable[[], None]) -> QSystemTrayIcon:
    tray = QSystemTrayIcon(QIcon(tray_icon_pixmap()))
    menu = QMenu()
    menu.addAction("FastWISPR").setEnabled(False)
    menu.addAction("Start recording", on_start)
    menu.addAction("Copy last transcript", hub.copy_last)
    menu.addAction("Open FastWISPR", hub.open_hub)
    menu.addAction("History", lambda: (hub.open_hub(), hub.show_page("history")))
    menu.addAction("Settings", lambda: (hub.open_hub(), hub.show_page("settings")))
    menu.addSeparator()
    menu.addAction("Pause hotkeys", on_pause)
    menu.addAction("Quit", QApplication.quit)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: hub.open_hub() if reason == QSystemTrayIcon.Trigger else None)
    tray.show()
    return tray
