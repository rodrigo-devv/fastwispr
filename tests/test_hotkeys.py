from fastwispr.windows.hotkeys import KeyboardHotkeyListener, KeyboardHotkeys


class FakeKeyboard:
    def __init__(self):
        self.registered = []
        self.unhooked = []

    def add_hotkey(self, hotkey, callback, suppress=False):
        handle = object()
        self.registered.append((hotkey, callback, suppress, handle))
        return handle

    def remove_hotkey(self, handle):
        self.unhooked.append(handle)


def test_keyboard_hotkey_listener_maps_ctrl_space_to_down_callback_without_suppressing_windows_events():
    keyboard = FakeKeyboard()
    calls = []
    listener = KeyboardHotkeyListener("ctrl+space", keyboard_module=keyboard)

    listener.start(lambda: calls.append("down"), lambda: calls.append("up"))
    hotkey, callback, suppress, handle = keyboard.registered[0]
    callback()
    listener.stop()

    assert hotkey == "ctrl+space"
    assert suppress is False
    assert calls == ["down"]
    assert keyboard.unhooked == [handle]


def test_keyboard_hotkeys_register_toggle_does_not_suppress_windows_events():
    keyboard = FakeKeyboard()
    calls = []
    hotkeys = KeyboardHotkeys(keyboard_module=keyboard)

    hotkeys.register_toggle("ctrl+space", lambda: calls.append("toggle"))
    hotkey, callback, suppress, _handle = keyboard.registered[0]
    callback()

    assert hotkey == "ctrl+space"
    assert suppress is False
    assert calls == ["toggle"]
