from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from typing import Callable, Sequence

from ..config import default_config_path

ProcessFactory = Callable[[Sequence[str]], subprocess.Popen]


class FastWisprTrayController:
    def __init__(
        self,
        *,
        config_path: Path | None = None,
        python_executable: str | None = None,
        module_mode: bool | None = None,
        process_factory: ProcessFactory | None = None,
        settings_callback: Callable[[Path], None] | None = None,
    ):
        self.config_path = config_path or default_config_path()
        self.python_executable = python_executable or sys.executable
        self.module_mode = module_mode if module_mode is not None else not bool(getattr(sys, "frozen", False))
        self.process_factory = process_factory or (lambda command: subprocess.Popen(list(command)))
        self.settings_callback = settings_callback
        self.process: subprocess.Popen | None = None

    def dictation_command(self) -> list[str]:
        command = [self.python_executable]
        if self.module_mode:
            command.extend(["-m", "fastwispr.cli"])
        command.extend(["--config", str(self.config_path), "run-windows-app"])
        return command

    def start_dictation(self, *_args: object) -> None:
        if self.is_running():
            return
        self.process = self.process_factory(self.dictation_command())

    def stop_dictation(self, *_args: object) -> None:
        if self.process is None:
            return
        process = self.process
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:  # pragma: no cover - defensive Windows path
                process.kill()
                process.wait(timeout=5)
        self.process = None

    def open_settings(self, *_args: object) -> None:
        if self.settings_callback is not None:
            self.settings_callback(self.config_path)
            return
        from .settings_ui import open_settings_window

        open_settings_window(self.config_path)

    def quit(self, icon=None, _item=None) -> None:
        self.stop_dictation()
        if icon is not None:
            icon.stop()

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def menu_labels(self) -> list[str]:
        return ["Start FastWispr", "Stop FastWispr", "Settings", "Quit"]


def run_tray(config_path: Path | None = None, *, autostart: bool = True) -> None:  # pragma: no cover - requires desktop tray
    import pystray

    controller = FastWisprTrayController(config_path=config_path)
    icon = pystray.Icon("FastWispr", _create_icon_image(), "FastWispr")
    icon.menu = pystray.Menu(
        pystray.MenuItem("Start FastWispr", controller.start_dictation),
        pystray.MenuItem("Stop FastWispr", controller.stop_dictation),
        pystray.MenuItem("Settings", controller.open_settings),
        pystray.MenuItem("Quit", controller.quit),
    )
    if autostart:
        controller.start_dictation()
    icon.run()


def _create_icon_image():  # pragma: no cover - visual asset
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (64, 64), (14, 18, 28))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 18, 56, 46), radius=14, fill=(34, 197, 94))
    draw.rectangle((20, 26, 44, 38), fill=(14, 18, 28))
    return image
