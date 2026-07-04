import pytest

from fastwispr.single_instance import (
    ERROR_ALREADY_EXISTS,
    AlreadyRunningError,
    SingleInstanceGuard,
    single_instance_smoke,
)


class FakeKernel32:
    def __init__(self, *, handle: int = 100, last_error: int = 0):
        self.handle = handle
        self.last_error = last_error
        self.closed = []
        self.created = []

    def CreateMutexW(self, _security, _initial_owner, name):
        self.created.append(name)
        return self.handle

    def CloseHandle(self, handle):
        self.closed.append(handle)
        return 1


def test_single_instance_guard_acquires_and_releases_windows_mutex():
    kernel32 = FakeKernel32(handle=123, last_error=0)
    guard = SingleInstanceGuard(
        "Local\\FastWisprTest",
        os_name="nt",
        kernel32=kernel32,
        last_error_getter=lambda: kernel32.last_error,
    )

    assert guard.acquire() is True
    assert kernel32.created == ["Local\\FastWisprTest"]

    guard.release()

    assert kernel32.closed == [123]


def test_single_instance_guard_rejects_existing_windows_mutex():
    kernel32 = FakeKernel32(handle=456, last_error=ERROR_ALREADY_EXISTS)
    guard = SingleInstanceGuard(
        "Local\\FastWisprTest",
        os_name="nt",
        kernel32=kernel32,
        last_error_getter=lambda: kernel32.last_error,
    )

    assert guard.acquire() is False
    assert kernel32.closed == [456]


def test_single_instance_context_raises_when_already_running():
    kernel32 = FakeKernel32(handle=789, last_error=ERROR_ALREADY_EXISTS)
    guard = SingleInstanceGuard(
        "Local\\FastWisprTest",
        os_name="nt",
        kernel32=kernel32,
        last_error_getter=lambda: kernel32.last_error,
    )

    with pytest.raises(AlreadyRunningError):
        with guard:
            pass


def test_single_instance_guard_is_noop_off_windows():
    guard = SingleInstanceGuard("Local\\FastWisprTest", os_name="posix")

    assert guard.acquire() is True
    guard.release()


def test_single_instance_smoke_detects_duplicate_mutex_with_fake_kernel32():
    class StatefulKernel32(FakeKernel32):
        def __init__(self):
            super().__init__(handle=900, last_error=0)
            self.seen = False

        def CreateMutexW(self, _security, _initial_owner, name):
            self.created.append(name)
            if self.seen:
                self.last_error = ERROR_ALREADY_EXISTS
                return 901
            self.seen = True
            self.last_error = 0
            return 900

    kernel32 = StatefulKernel32()

    assert single_instance_smoke(
        "Local\\FastWisprSmokeTest",
        os_name="nt",
        kernel32=kernel32,
        last_error_getter=lambda: kernel32.last_error,
    ) is True
    assert kernel32.closed == [901, 900]
