import sys
from types import SimpleNamespace

import pytest

from fastwispr.windows.injector import ClipboardPasteInjector


class FakePyperclip:
    def __init__(self):
        self.value = "previous"
        self.copies = []

    def paste(self):
        return self.value

    def copy(self, text):
        self.copies.append(text)
        self.value = text


class FailingPyAutoGui:
    def hotkey(self, *keys):
        raise RuntimeError("paste failed")


def test_clipboard_is_restored_when_paste_hotkey_fails(monkeypatch):
    pyperclip = FakePyperclip()
    monkeypatch.setitem(sys.modules, "pyperclip", pyperclip)
    monkeypatch.setitem(sys.modules, "pyautogui", FailingPyAutoGui())
    monkeypatch.setattr("time.sleep", lambda _seconds: None)
    injector = ClipboardPasteInjector(restore_clipboard=True)

    with pytest.raises(RuntimeError, match="paste failed"):
        injector.paste_text("dictated text")

    assert pyperclip.value == "previous"
    assert pyperclip.copies == ["dictated text", "previous"]
