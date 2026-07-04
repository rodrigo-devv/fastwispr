from __future__ import annotations

import time


class ClipboardPasteInjector:
    def __init__(self, restore_clipboard: bool = True, paste_delay_seconds: float = 0.05):
        try:
            import pyautogui
            import pyperclip
        except ImportError as exc:
            raise RuntimeError("Install Windows paste support with: python -m pip install -e '.[windows]'") from exc
        self.pyautogui = pyautogui
        self.pyperclip = pyperclip
        self.restore_clipboard = restore_clipboard
        self.paste_delay_seconds = paste_delay_seconds

    def paste_text(self, text: str) -> None:
        previous = None
        if self.restore_clipboard:
            try:
                previous = self.pyperclip.paste()
            except Exception:
                previous = None
        try:
            self.pyperclip.copy(text)
            time.sleep(self.paste_delay_seconds)
            self.pyautogui.hotkey("ctrl", "v")
            time.sleep(self.paste_delay_seconds)
        finally:
            if self.restore_clipboard and previous is not None:
                self.pyperclip.copy(previous)
