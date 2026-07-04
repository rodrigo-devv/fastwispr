from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast


class KeyboardHotkeys:
    def __init__(self, keyboard_module: Any | None = None):
        if keyboard_module is None:
            try:
                keyboard_module = __import__("keyboard")
            except ImportError as exc:
                raise RuntimeError("Install Windows hotkey support with: python -m pip install -e '.[windows]'") from exc
        self.keyboard = cast(Any, keyboard_module)

    def register_toggle(self, hotkey: str, callback: Callable[[], None]) -> None:
        self.keyboard.add_hotkey(hotkey, callback, suppress=False)

    def wait_forever(self) -> None:
        self.keyboard.wait()


class KeyboardHotkeyListener:
    """Listener adapter matching the mouse listener's start/stop shape.

    The Python `keyboard` package gives a reliable global combo trigger for Ctrl+Space,
    but combo release handling is not worth making clever here. Use this listener with
    activation.mode="toggle". Mouse remains available for true hold-to-talk.
    """

    def __init__(self, hotkey: str = "ctrl+space", keyboard_module: Any | None = None):
        if keyboard_module is None:
            try:
                keyboard_module = __import__("keyboard")
            except ImportError as exc:
                raise RuntimeError("Install Windows hotkey support with: python -m pip install -e '.[windows]'") from exc
        self.keyboard = cast(Any, keyboard_module)
        self.hotkey = hotkey
        self.handle: object | None = None

    def start(self, on_down: Callable[[], None], on_up: Callable[[], None]) -> None:
        self.handle = self.keyboard.add_hotkey(self.hotkey, on_down, suppress=False)

    def stop(self) -> None:
        if self.handle is not None:
            self.keyboard.remove_hotkey(self.handle)
            self.handle = None
