from fastwispr.cli import normalize_argv_for_packaged_app


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
