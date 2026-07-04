from fastwispr.cli import normalize_argv_for_packaged_app, run_with_single_instance


class FakeGuard:
    def __init__(self, _name, *, should_enter=True):
        self.should_enter = should_enter
        self.entered = False

    def __enter__(self):
        self.entered = True
        if not self.should_enter:
            from fastwispr.single_instance import AlreadyRunningError

            raise AlreadyRunningError("already running")
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_packaged_app_without_args_defaults_to_tray():
    assert normalize_argv_for_packaged_app(
        [],
        frozen=True,
        executable_path=r"C:\development\fastwispr\dist\FastWispr\FastWispr.exe",
    ) == ["run-windows-tray"]


def test_packaged_cli_without_args_still_prints_help():
    assert normalize_argv_for_packaged_app(
        [],
        frozen=True,
        executable_path=r"C:\development\fastwispr\dist\FastWisprCli\FastWisprCli.exe",
    ) == []


def test_source_cli_without_args_still_prints_help():
    assert normalize_argv_for_packaged_app([], frozen=False) == []


def test_packaged_exe_with_args_keeps_requested_command():
    assert normalize_argv_for_packaged_app(["windows-smoke"], frozen=True) == ["windows-smoke"]


def test_run_with_single_instance_runs_action_when_mutex_is_free():
    calls = []
    notices = []

    result = run_with_single_instance(
        "Local\\FastWisprTray",
        "FastWispr já está aberto.",
        lambda: calls.append("started"),
        guard_factory=lambda name: FakeGuard(name, should_enter=True),
        notifier=notices.append,
    )

    assert result == 0
    assert calls == ["started"]
    assert notices == []


def test_run_with_single_instance_notifies_and_skips_action_when_duplicate():
    calls = []
    notices = []

    result = run_with_single_instance(
        "Local\\FastWisprTray",
        "FastWispr já está aberto.",
        lambda: calls.append("started"),
        guard_factory=lambda name: FakeGuard(name, should_enter=False),
        notifier=notices.append,
    )

    assert result == 0
    assert calls == []
    assert notices == ["FastWispr já está aberto."]
