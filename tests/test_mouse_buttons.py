import ctypes
from ctypes import wintypes

from fastwispr.windows.mouse_buttons import LowLevelMouseProc, configure_mouse_hook_api, xbutton_name_from_mouse_data


def test_xbutton_name_from_mouse_data_identifies_side_buttons():
    assert xbutton_name_from_mouse_data(0x00010000) == "xbutton1"
    assert xbutton_name_from_mouse_data(0x00020000) == "xbutton2"
    assert xbutton_name_from_mouse_data(0) is None


class FakeFn:
    argtypes = None
    restype = None


class FakeDll:
    def __init__(self, *names: str):
        for name in names:
            setattr(self, name, FakeFn())


def test_configure_mouse_hook_api_uses_pointer_sized_winapi_types():
    user32 = FakeDll(
        "SetWindowsHookExW",
        "UnhookWindowsHookEx",
        "CallNextHookEx",
        "GetMessageW",
        "TranslateMessage",
        "DispatchMessageW",
    )
    kernel32 = FakeDll("GetModuleHandleW")

    configure_mouse_hook_api(user32, kernel32)

    assert kernel32.GetModuleHandleW.argtypes == [wintypes.LPCWSTR]
    assert kernel32.GetModuleHandleW.restype == wintypes.HMODULE
    assert user32.SetWindowsHookExW.argtypes == [ctypes.c_int, LowLevelMouseProc, wintypes.HINSTANCE, wintypes.DWORD]
    assert user32.SetWindowsHookExW.restype == wintypes.HHOOK
