from __future__ import annotations

import time


class PasteFailed(RuntimeError):
    """Paste hotkey failed; the transcript stays on the clipboard."""


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

    def copy_text(self, text: str) -> None:
        self.pyperclip.copy(text)

    def paste_text(self, text: str) -> None:
        previous = None
        if self.restore_clipboard:
            try:
                previous = self.pyperclip.paste()
            except Exception:
                previous = None
        self.copy_text(text)
        time.sleep(self.paste_delay_seconds)
        try:
            self.pyautogui.hotkey("ctrl", "v")
            time.sleep(self.paste_delay_seconds)
        except Exception as exc:
            # Leave dictated text on the clipboard so Ctrl+V still works.
            raise PasteFailed(str(exc)) from exc
        if self.restore_clipboard and previous is not None:
            self.pyperclip.copy(previous)
