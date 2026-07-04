from __future__ import annotations

from collections.abc import Callable
import ctypes
from ctypes import wintypes
import threading

WH_MOUSE_LL = 14
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C
HC_ACTION = 0
XBUTTON1 = 0x0001
XBUTTON2 = 0x0002
LRESULT = getattr(wintypes, "LRESULT", wintypes.LPARAM)
ULONG_PTR = getattr(wintypes, "ULONG_PTR", wintypes.WPARAM)


def xbutton_name_from_mouse_data(mouse_data: int) -> str | None:
    xbutton = (mouse_data >> 16) & 0xFFFF
    if xbutton == XBUTTON1:
        return "xbutton1"
    if xbutton == XBUTTON2:
        return "xbutton2"
    return None


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


LowLevelMouseProc = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)


def configure_mouse_hook_api(user32, kernel32) -> None:
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE

    user32.SetWindowsHookExW.argtypes = [ctypes.c_int, LowLevelMouseProc, wintypes.HINSTANCE, wintypes.DWORD]
    user32.SetWindowsHookExW.restype = wintypes.HHOOK
    user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
    user32.UnhookWindowsHookEx.restype = wintypes.BOOL
    user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
    user32.CallNextHookEx.restype = LRESULT
    user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    user32.GetMessageW.restype = wintypes.BOOL
    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.TranslateMessage.restype = wintypes.BOOL
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.restype = LRESULT


class XButtonHoldListener:
    def __init__(self, button: str = "xbutton1"):
        if button not in {"xbutton1", "xbutton2"}:
            raise ValueError("button must be xbutton1 or xbutton2")
        self.button = button
        self.on_press: Callable[[], None] | None = None
        self.on_release: Callable[[], None] | None = None
        self._hook: int | None = None
        self._thread: threading.Thread | None = None
        self._proc = LowLevelMouseProc(self._handle)
        win_dll = getattr(ctypes, "WinDLL", None)
        if win_dll is None:
            raise RuntimeError("Mouse side-button hooks require Windows")
        self._user32 = win_dll("user32", use_last_error=True)
        self._kernel32 = win_dll("kernel32", use_last_error=True)
        configure_mouse_hook_api(self._user32, self._kernel32)

    def start(self, on_press: Callable[[], None], on_release: Callable[[], None]) -> None:
        self.on_press = on_press
        self.on_release = on_release
        self._thread = threading.Thread(target=self._run, name="fastwispr-xbutton-listener", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._hook:
            self._user32.UnhookWindowsHookEx(self._hook)
            self._hook = None

    def _run(self) -> None:
        self._hook = self._user32.SetWindowsHookExW(WH_MOUSE_LL, self._proc, self._kernel32.GetModuleHandleW(None), 0)
        if not self._hook:
            error_code = getattr(ctypes, "get_last_error", lambda: 0)()
            win_error = getattr(ctypes, "WinError", None)
            if win_error is not None:
                raise win_error(error_code)
            raise OSError(error_code)
        msg = wintypes.MSG()
        while self._user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            self._user32.TranslateMessage(ctypes.byref(msg))
            self._user32.DispatchMessageW(ctypes.byref(msg))

    def _handle(self, n_code: int, w_param: int, l_param: int) -> int:
        if n_code == HC_ACTION and w_param in {WM_XBUTTONDOWN, WM_XBUTTONUP}:
            data = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            button = xbutton_name_from_mouse_data(data.mouseData)
            if button == self.button:
                if w_param == WM_XBUTTONDOWN and self.on_press is not None:
                    self.on_press()
                if w_param == WM_XBUTTONUP and self.on_release is not None:
                    self.on_release()
                return 1
        return self._user32.CallNextHookEx(self._hook, n_code, w_param, l_param)
