from __future__ import annotations

from collections.abc import Callable
import ctypes
import os
import sys
from types import TracebackType
from typing import Any

ERROR_ALREADY_EXISTS = 183

APP_MUTEX_NAME = "Local\\FastWisprTray"
ENGINE_MUTEX_NAME = "Local\\FastWisprEngine"
APP_ALREADY_RUNNING_MESSAGE = "FastWispr já está aberto. Use o ícone na bandeja do Windows."
ENGINE_ALREADY_RUNNING_MESSAGE = "FastWispr já está em execução. Use o ícone na bandeja do Windows."


class AlreadyRunningError(RuntimeError):
    """Raised when a named single-instance mutex already exists."""


class SingleInstanceGuard:
    def __init__(
        self,
        name: str,
        *,
        os_name: str | None = None,
        kernel32: Any | None = None,
        last_error_getter: Callable[[], int] | None = None,
    ):
        self.name = name
        self.os_name = os.name if os_name is None else os_name
        self.kernel32 = kernel32
        self.last_error_getter = last_error_getter
        self.handle: int | None = None

    def __enter__(self) -> SingleInstanceGuard:
        if not self.acquire():
            raise AlreadyRunningError(self.name)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        self.release()
        return False

    def acquire(self) -> bool:
        if self.os_name != "nt":
            return True

        kernel32 = self.kernel32 or _kernel32()
        last_error_getter = self.last_error_getter or ctypes.get_last_error
        handle = kernel32.CreateMutexW(None, False, self.name)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())

        last_error = last_error_getter()
        if last_error == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(handle)
            return False

        self.handle = handle
        return True

    def release(self) -> None:
        if self.os_name != "nt" or self.handle is None:
            self.handle = None
            return

        kernel32 = self.kernel32 or _kernel32()
        kernel32.CloseHandle(self.handle)
        self.handle = None


def _kernel32():
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return kernel32


def show_already_running_message(message: str, *, title: str = "FastWispr") -> None:
    if os.name == "nt":
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
        user32.MessageBoxW.restype = ctypes.c_int
        mb_ok = 0x00000000
        mb_icon_information = 0x00000040
        user32.MessageBoxW(None, message, title, mb_ok | mb_icon_information)
        return

    print(message, file=sys.stderr)


def single_instance_smoke(
    mutex_name: str = "Local\\FastWisprSmoke",
    *,
    os_name: str | None = None,
    kernel32: Any | None = None,
    last_error_getter: Callable[[], int] | None = None,
) -> bool:
    effective_os_name = os.name if os_name is None else os_name
    first = SingleInstanceGuard(
        mutex_name,
        os_name=effective_os_name,
        kernel32=kernel32,
        last_error_getter=last_error_getter,
    )
    second = SingleInstanceGuard(
        mutex_name,
        os_name=effective_os_name,
        kernel32=kernel32,
        last_error_getter=last_error_getter,
    )
    acquired_first = first.acquire()
    try:
        acquired_second = second.acquire()
        try:
            if effective_os_name == "nt":
                return acquired_first and not acquired_second
            return acquired_first and acquired_second
        finally:
            second.release()
    finally:
        first.release()
