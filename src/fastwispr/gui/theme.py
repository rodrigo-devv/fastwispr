from __future__ import annotations

from datetime import datetime

HUB_DEFAULT = (400, 560)
HUB_MIN = (380, 520)
HUB_MAX = (460, 620)
HUB_INSET_RIGHT = 20
HUB_INSET_BOTTOM = 16
TITLEBAR_H = 52
PAGEBAR_H = 44
FOOTER_H = 34
OVERLAY_H = 38
OVERLAY_MIN_W = 140
OVERLAY_TOP = 24
OVERLAY_PAD_X = 13
CHIP_H = 46
SEARCH_H = 34
ROW_H = 46
COPY_BTN = 28
TOAST_MAX = (280, 40)

THEMES = {
    "dark": {
        "bg": "#090A0B",
        "surface": "#111315",
        "surface_2": "#17191C",
        "surface_hover": "#1D2024",
        "border": "#272A2E",
        "border_hover": "#363A40",
        "text": "#F5F5F5",
        "text_secondary": "#A1A1AA",
        "text_muted": "#71717A",
        "accent": "#E10600",
        "accent_hover": "#FF1A14",
        "accent_soft": "rgba(225, 6, 0, 0.12)",
        "success": "#22C55E",
        "warning": "#F59E0B",
        "error": "#EF4444",
    },
    "light": {
        "bg": "#FFFFFF",
        "surface": "#F7F7F7",
        "surface_2": "#F0F0F0",
        "surface_hover": "#EAEAEA",
        "border": "#E2E2E2",
        "border_hover": "#D2D2D2",
        "text": "#111111",
        "text_secondary": "#5F6368",
        "text_muted": "#858585",
        "accent": "#D60000",
        "accent_hover": "#E10600",
        "accent_soft": "rgba(214, 0, 0, 0.08)",
        "success": "#16A34A",
        "warning": "#D97706",
        "error": "#DC2626",
    },
}

STATUS_READY = "ready"
STATUS_RECORDING = "recording"
STATUS_PROCESSING = "processing"
STATUS_ERROR = "error"


def resolve_theme_name(preference: str, system_is_dark: bool = True) -> str:
    name = (preference or "dark").strip().lower()
    if name == "system":
        return "dark" if system_is_dark else "light"
    return name if name in THEMES else "dark"


def theme_tokens(preference: str, system_is_dark: bool = True) -> dict[str, str]:
    return THEMES[resolve_theme_name(preference, system_is_dark)]


def hub_top_left(avail_right: int, avail_bottom: int, width: int, height: int) -> tuple[int, int]:
    # Logical pixels: 20px from the right, 16px above the taskbar.
    return (avail_right - width - HUB_INSET_RIGHT, avail_bottom - height - HUB_INSET_BOTTOM)


def overlay_enter_pos(screen_right: int, pill_width: int, top: int = OVERLAY_TOP) -> tuple[int, int]:
    return (screen_right + pill_width + 24, top)


def overlay_rest_pos(screen_width: int, pill_width: int, top: int = OVERLAY_TOP) -> tuple[int, int]:
    return ((screen_width - pill_width) // 2, top)


def model_chip_label(stt_model: str) -> str:
    return f"whisper-{stt_model.strip()}" if stt_model.strip() else "whisper-small"


def hotkey_keycaps(hotkey: str) -> list[str]:
    labels = {
        "ctrl": "Ctrl",
        "control": "Ctrl",
        "alt": "Alt",
        "shift": "Shift",
        "space": "Space",
        "win": "Win",
    }
    return [labels.get(part.strip().lower(), part.strip().capitalize()) for part in hotkey.split("+") if part.strip()]


def format_duration_ms(duration_ms: int | None) -> str:
    ms = 0 if duration_ms is None else max(0, int(duration_ms))
    return f"{ms / 1000:.1f}s"


def format_clock(created_at: str) -> str:
    stamp = _parse_created(created_at)
    return stamp.strftime("%H:%M") if stamp else created_at


def history_group_label(created_at: str, now: datetime | None = None) -> str:
    stamp = _parse_created(created_at)
    if stamp is None:
        return "Earlier"
    today = (now or datetime.now()).date()
    delta = (today - stamp.date()).days
    if delta <= 0:
        return "Today"
    if delta == 1:
        return "Yesterday"
    return stamp.strftime("%d %b %Y")


def history_meta_line(created_at: str, duration_ms: int | None, now: datetime | None = None) -> str:
    group = history_group_label(created_at, now)
    return f"{group} · {format_clock(created_at)} · {format_duration_ms(duration_ms)}"


def preset_label(stt_model: str) -> str:
    mapping = {"base": "Fast", "small": "Balanced", "medium": "Accurate"}
    return mapping.get(stt_model, "Custom")


def app_qss(tokens: dict[str, str]) -> str:
    return f"""
QWidget#AppShell {{
  background: transparent;
  color: {tokens['text']};
  border: none;
  font-family: "Segoe UI", sans-serif;
}}
QFrame#SectionDivider {{
  background: {tokens['border']};
  border: none;
  max-height: 1px;
  min-height: 1px;
}}
QWidget#TitleBar {{
  background: {tokens['bg']};
  border-bottom: 1px solid {tokens['border']};
}}
QWidget#PageBar {{
  background: {tokens['bg']};
  border-bottom: 1px solid {tokens['border']};
}}
QLabel {{
  color: {tokens['text']};
  font-size: 13px;
  font-family: "Segoe UI", sans-serif;
}}
QLabel#WordmarkFast {{
  color: {tokens['text']};
  font-size: 14px;
  font-weight: 600;
}}
QLabel#WordmarkWispr {{
  color: {tokens['accent']};
  font-size: 14px;
  font-weight: 600;
}}
QLabel#StatusLabel {{
  font-size: 20px;
  font-weight: 600;
}}
QLabel#Secondary, QLabel#Meta {{
  color: {tokens['text_muted']};
  font-size: 11px;
}}
QLabel#Hint {{
  color: {tokens['text_secondary']};
  font-size: 13px;
}}
QFrame#ChromeDivider {{
  background: {tokens['border']};
  border: none;
  max-width: 1px;
}}
QPushButton {{
  background: {tokens['surface']};
  color: {tokens['text']};
  border: 1px solid {tokens['border']};
  border-radius: 5px;
  font-size: 12px;
  font-weight: 500;
  padding: 0 14px;
  min-height: 34px;
  font-family: "Segoe UI", sans-serif;
}}
QPushButton:hover {{
  background: {tokens['surface_hover']};
  border-color: {tokens['border_hover']};
}}
QPushButton:focus {{
  border: 1px solid {tokens['accent']};
}}
QPushButton#Primary {{
  background: {tokens['accent']};
  color: #FFFFFF;
  border: 1px solid {tokens['accent']};
  font-weight: 600;
}}
QPushButton#Primary:hover {{
  background: {tokens['accent_hover']};
}}
QPushButton#Ghost {{
  background: transparent;
  color: {tokens['text_secondary']};
  border: 1px solid transparent;
  border-radius: 5px;
}}
QPushButton#Ghost:hover {{
  background: {tokens['surface_hover']};
  color: {tokens['text']};
}}
QPushButton#IconBtn {{
  background: transparent;
  border: 1px solid transparent;
  border-radius: 5px;
  padding: 0px;
  min-height: 32px;
  max-height: 32px;
  min-width: 32px;
  max-width: 32px;
}}
QPushButton#IconBtn:hover {{
  background: {tokens['surface_hover']};
}}
QPushButton#CaptionBtn {{
  background: transparent;
  border: none;
  border-radius: 0px;
  padding: 0px;
  min-width: 40px;
  max-width: 40px;
  min-height: 52px;
  max-height: 52px;
}}
QPushButton#CaptionBtn:hover {{
  background: {tokens['surface_hover']};
}}
QPushButton#CaptionClose {{
  background: transparent;
  border: none;
  border-radius: 0px;
  padding: 0px;
  min-width: 40px;
  max-width: 40px;
  min-height: 52px;
  max-height: 52px;
}}
QPushButton#CaptionClose:hover {{
  background: {tokens['accent_soft']};
}}
QPushButton#CopyBtn {{
  background: transparent;
  border: 1px solid transparent;
  border-radius: 5px;
  min-width: 28px;
  max-width: 28px;
  min-height: 28px;
  max-height: 28px;
  padding: 0px;
}}
QPushButton#CopyBtn:hover {{
  background: {tokens['surface_hover']};
}}
QPushButton#Chip {{
  background: {tokens['surface']};
  border: 1px solid {tokens['border']};
  border-radius: 5px;
  text-align: left;
  padding: 0 12px;
  min-height: 46px;
}}
QPushButton#Chip:hover {{
  background: {tokens['surface_hover']};
  border-color: {tokens['border_hover']};
}}
QLineEdit, QPlainTextEdit {{
  background: {tokens['surface']};
  color: {tokens['text']};
  border: 1px solid {tokens['border']};
  border-radius: 5px;
  padding: 0 10px;
  font-size: 13px;
  min-height: {SEARCH_H}px;
  font-family: "Segoe UI", sans-serif;
}}
QLineEdit:focus, QPlainTextEdit:focus {{
  border: 1px solid {tokens['accent']};
}}
QFrame#Card, QFrame#Chip, QFrame#Keycap {{
  background: {tokens['surface']};
  border: 1px solid {tokens['border']};
  border-radius: 5px;
}}
QFrame#TranscriptPanel {{
  background: {tokens['surface']};
  border: 1px solid {tokens['border']};
  border-radius: 7px;
}}
QMenu {{
  background: {tokens['surface']};
  color: {tokens['text']};
  border: 1px solid {tokens['border']};
  border-radius: 7px;
  padding: 4px;
  font-size: 12px;
}}
QMenu::item {{
  height: 30px;
  padding: 0 9px;
  border-radius: 4px;
}}
QMenu::item:selected {{
  background: {tokens['surface_hover']};
}}
QScrollArea {{
  border: none;
  background: {tokens['bg']};
}}
"""


def _parse_created(created_at: str) -> datetime | None:
    text = created_at.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(text[:26], fmt)
        except ValueError:
            continue
    return None
