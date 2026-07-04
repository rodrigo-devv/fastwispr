from pathlib import Path

from fastwispr.windows.tray import FastWisprTrayController


class FakeProcess:
    def __init__(self):
        self.terminated = False
        self.waited = False

    def poll(self):
        return None if not self.terminated else 0

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.waited = True
        return 0


def test_tray_controller_starts_dictation_subprocess_with_config(tmp_path: Path):
    calls = []
    fake = FakeProcess()

    controller = FastWisprTrayController(
        config_path=tmp_path / "config.toml",
        python_executable="python-test",
        process_factory=lambda cmd: calls.append(cmd) or fake,
    )

    controller.start_dictation()
    controller.start_dictation()

    assert len(calls) == 1
    assert calls[0] == [
        "python-test",
        "-m",
        "fastwispr.cli",
        "--config",
        str(tmp_path / "config.toml"),
        "run-windows-app",
    ]


def test_tray_controller_uses_exe_command_when_packaged(tmp_path: Path):
    controller = FastWisprTrayController(
        config_path=tmp_path / "config.toml",
        python_executable="FastWispr.exe",
        module_mode=False,
    )

    assert controller.dictation_command() == [
        "FastWispr.exe",
        "--config",
        str(tmp_path / "config.toml"),
        "run-windows-app",
    ]


def test_tray_controller_stops_running_process(tmp_path: Path):
    fake = FakeProcess()
    controller = FastWisprTrayController(
        config_path=tmp_path / "config.toml",
        process_factory=lambda cmd: fake,
    )

    controller.start_dictation()
    controller.stop_dictation()

    assert fake.terminated is True
    assert fake.waited is True


def test_tray_menu_labels_are_stable(tmp_path: Path):
    controller = FastWisprTrayController(config_path=tmp_path / "config.toml")

    assert controller.menu_labels() == ["Start FastWispr", "Stop FastWispr", "Settings", "Open Logs", "Quit"]


def test_tray_controller_opens_log_file(tmp_path: Path):
    opened = []
    log_path = tmp_path / "fastwispr.log"
    controller = FastWisprTrayController(
        config_path=tmp_path / "config.toml",
        log_path_factory=lambda: log_path,
        open_path_callback=opened.append,
    )

    controller.open_logs()

    assert opened == [log_path]
    assert log_path.exists()
