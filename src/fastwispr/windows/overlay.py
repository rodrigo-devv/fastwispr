from __future__ import annotations

import math
from typing import Literal, TypedDict

OverlayState = Literal["idle", "recording", "processing", "pasting", "error"]
OverlayLayoutState = Literal["recording", "processing"]
WAVEFORM_ACTIVITY_THRESHOLD = 0.01
WAVEFORM_LEVEL_GAIN = 6.0
WAVEFORM_MAX_HEIGHT = 16


class OverlayLayout(TypedDict, total=False):
    size: tuple[int, int]
    pill: tuple[int, int, int, int]
    waveform: tuple[int, int, int, int]
    waveform_center_y: int
    spinner_center: tuple[int, int]


class OverlayTheme(TypedDict):
    transparent: str
    panel: str
    waveform: str
    idle_waveform: str
    spinner: str


def overlay_theme() -> OverlayTheme:
    return {
        "transparent": "#010203",
        "panel": "#000000",
        "waveform": "#f2f2f2",
        "idle_waveform": "#8c8c8c",
        "spinner": "#bdbdbd",
    }


def overlay_layout(state: OverlayLayoutState = "recording") -> OverlayLayout:
    if state == "processing":
        return {
            "size": (141, 37),
            "pill": (0, 0, 141, 37),
            "waveform": (18, 9, 98, 28),
            "waveform_center_y": 18,
            "spinner_center": (122, 18),
        }
    return {
        "size": (141, 37),
        "pill": (0, 0, 141, 37),
        "waveform": (18, 9, 123, 28),
        "waveform_center_y": 18,
    }


def _clamp_level(level: float) -> float:
    return max(0.0, min(1.0, float(level)))


def append_level_history(history: list[float], level: float, *, limit: int = 32) -> list[float]:
    return [*history, _clamp_level(level)][-limit:]


def _sample_history(history: list[float], *, count: int) -> list[float]:
    if count <= 0:
        return []
    if not history:
        return [0.0] * count
    if len(history) == count:
        return [_clamp_level(level) for level in history]
    if len(history) < count:
        return [0.0] * (count - len(history)) + [_clamp_level(level) for level in history]
    return [_clamp_level(level) for level in history[-count:]]


def idle_waveform_bar_heights(*, count: int = 14, phase: int = 0) -> list[int]:
    heights: list[int] = []
    for i in range(count):
        pulse = math.sin((i + phase) * 0.65) * 0.5 + math.sin((i + phase) * 0.19) * 0.5
        heights.append(2 + int(max(0.0, pulse) * 2))
    return heights


def waveform_bar_heights_from_history(
    history: list[float],
    *,
    count: int = 14,
    max_height: int = WAVEFORM_MAX_HEIGHT,
    floor: int = 2,
) -> list[int]:
    usable = max(1, max_height - floor)
    heights: list[int] = []
    for level in _sample_history(history, count=count):
        visible_level = min(1.0, level * WAVEFORM_LEVEL_GAIN) ** 0.55 if level > 0 else 0.0
        heights.append(int(floor + usable * visible_level))
    return heights


def waveform_bar_heights(level: float, *, count: int = 14, max_height: int = WAVEFORM_MAX_HEIGHT, phase: int = 0) -> list[int]:
    del phase
    return waveform_bar_heights_from_history([_clamp_level(level)] * count, count=count, max_height=max_height)


def display_segments_from_history(
    history: list[float],
    silence_threshold: float = WAVEFORM_ACTIVITY_THRESHOLD,
    *,
    count: int = 14,
    phase: int = 0,
) -> list[int]:
    recent = history[-8:]
    if not recent or max(recent) < silence_threshold:
        return idle_waveform_bar_heights(count=count, phase=phase)
    return waveform_bar_heights_from_history(history, count=count)


def display_segments(level: float, silence_threshold: float = WAVEFORM_ACTIVITY_THRESHOLD, *, count: int = 14, phase: int = 0) -> list[int]:
    if level < silence_threshold:
        return idle_waveform_bar_heights(count=count, phase=phase)
    return waveform_bar_heights(level, count=count)


def spinner_tick_angles(*, phase: int, count: int = 8) -> list[int]:
    return [int(((i + phase) % count) * 360 / count) for i in range(count)]


class FloatingAudioOverlay:
    def __init__(self):
        import tkinter as tk

        self.tk = tk
        self.theme = overlay_theme()
        self.level = 0.0
        self.level_history: list[float] = []
        self.state: OverlayState = "idle"
        self.phase = 0
        self.transparent_color = self.theme["transparent"]
        width, height = overlay_layout("recording")["size"]
        self.width = width
        self.height = height
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-alpha", 0.96)
            self.root.attributes("-transparentcolor", self.transparent_color)
        except Exception:
            pass
        self.root.configure(bg=self.transparent_color)
        self.canvas = tk.Canvas(
            self.root,
            width=self.width,
            height=self.height,
            bg=self.transparent_color,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self._center_top()
        self.root.after(33, self._tick)

    def _layout_state(self) -> OverlayLayoutState:
        if self.state in {"processing", "pasting", "error"}:
            return "processing"
        return "recording"

    def _apply_geometry(self) -> None:
        width, height = overlay_layout(self._layout_state())["size"]
        if (width, height) != (self.width, self.height):
            self.width = width
            self.height = height
            self.canvas.configure(width=width, height=height)
        self._center_top()

    def _center_top(self) -> None:
        screen_width = self.root.winfo_screenwidth()
        x = max(0, int((screen_width - self.width) / 2))
        self.root.geometry(f"{self.width}x{self.height}+{x}+24")

    def make_no_activate(self) -> None:
        try:
            import ctypes
            from ctypes import wintypes

            hwnd = self.root.winfo_id()
            windll = getattr(ctypes, "windll")
            get_style = getattr(windll.user32, "GetWindowLongPtrW", windll.user32.GetWindowLongW)
            set_style = getattr(windll.user32, "SetWindowLongPtrW", windll.user32.SetWindowLongW)
            get_style.argtypes = [wintypes.HWND, ctypes.c_int]
            get_style.restype = ctypes.c_void_p
            set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
            set_style.restype = ctypes.c_void_p
            exstyle = int(get_style(hwnd, -20) or 0)
            exstyle |= 0x08000000  # WS_EX_NOACTIVATE
            exstyle |= 0x00000080  # WS_EX_TOOLWINDOW
            exstyle |= 0x00000020  # WS_EX_TRANSPARENT, click-through
            set_style(hwnd, -20, exstyle)
        except Exception:
            pass

    def show(self) -> None:
        self._apply_geometry()
        self.root.deiconify()
        self.root.lift()
        self.make_no_activate()

    def hide(self) -> None:
        self.root.withdraw()

    def set_state(self, state: OverlayState) -> None:
        previous = self.state
        self.state = state
        if state == "recording" and previous != "recording":
            self.level = 0.0
            self.level_history = []
            self.phase = 0
        if state == "idle":
            self.hide()
        else:
            self.show()
        self._draw()

    def set_level(self, level: float) -> None:
        self.level = _clamp_level(level)
        self.level_history = append_level_history(self.level_history, self.level)

    def run(self) -> None:
        self.root.mainloop()

    def close(self) -> None:
        self.root.destroy()

    def _tick(self) -> None:
        self.phase = (self.phase + 1) % 1000
        if self.state == "recording":
            self.level = max(0.0, self.level * 0.9)
            self.level_history = append_level_history(self.level_history, self.level)
        self._draw()
        self.root.after(33, self._tick)

    def _draw(self) -> None:
        self.canvas.delete("all")
        if self.state == "idle":
            return
        if self.state == "recording":
            self._draw_recording()
            return
        self._draw_processing()

    def _draw_recording(self) -> None:
        layout = overlay_layout("recording")
        self._rounded_rect(*layout["pill"], 19, fill=self.theme["panel"])
        self._draw_waveform(layout, count=16)

    def _draw_processing(self) -> None:
        layout = overlay_layout("processing")
        self._rounded_rect(*layout["pill"], 19, fill=self.theme["panel"])
        self._draw_waveform(layout, count=14, forced_color=self.theme["idle_waveform"])
        self._draw_spinner(layout["spinner_center"])

    def _rounded_rect(self, x0: int, y0: int, x1: int, y1: int, radius: int, *, fill: str) -> None:
        diameter = radius * 2
        self.canvas.create_arc(x0, y0, x0 + diameter, y0 + diameter, start=90, extent=90, fill=fill, outline=fill)
        self.canvas.create_arc(x1 - diameter, y0, x1, y0 + diameter, start=0, extent=90, fill=fill, outline=fill)
        self.canvas.create_arc(x1 - diameter, y1 - diameter, x1, y1, start=270, extent=90, fill=fill, outline=fill)
        self.canvas.create_arc(x0, y1 - diameter, x0 + diameter, y1, start=180, extent=90, fill=fill, outline=fill)
        self.canvas.create_rectangle(x0 + radius, y0, x1 - radius, y1, fill=fill, outline=fill)
        self.canvas.create_rectangle(x0, y0 + radius, x1, y1 - radius, fill=fill, outline=fill)

    def _draw_waveform(self, layout: OverlayLayout, *, count: int, forced_color: str | None = None) -> None:
        left, _, right, _ = layout["waveform"]
        center_y = layout["waveform_center_y"]
        if forced_color is not None:
            heights = idle_waveform_bar_heights(count=count, phase=self.phase)
            color = forced_color
        elif max(self.level_history[-8:] or [0.0]) < WAVEFORM_ACTIVITY_THRESHOLD:
            heights = idle_waveform_bar_heights(count=count, phase=self.phase)
            color = self.theme["idle_waveform"]
        else:
            heights = waveform_bar_heights_from_history(self.level_history, count=count)
            color = self.theme["waveform"]
        gap = (right - left) / max(1, len(heights) - 1)
        for i, height in enumerate(heights):
            x = int(left + gap * i)
            self.canvas.create_line(
                x,
                center_y - height / 2,
                x,
                center_y + height / 2,
                fill=color,
                width=2,
                capstyle="round",
            )

    def _draw_spinner(self, center: tuple[int, int]) -> None:
        cx, cy = center
        outer = 11
        inner = 6
        for index, angle in enumerate(spinner_tick_angles(phase=self.phase // 2, count=8)):
            radians = math.radians(angle)
            shade = 80 + index * 18
            color = f"#{shade:02x}{shade:02x}{shade:02x}"
            self.canvas.create_line(
                cx + math.cos(radians) * inner,
                cy + math.sin(radians) * inner,
                cx + math.cos(radians) * outer,
                cy + math.sin(radians) * outer,
                fill=color,
                width=2,
                capstyle="round",
            )
