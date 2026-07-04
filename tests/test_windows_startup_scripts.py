from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_startup_scripts_install_and_remove_fastwispr_shortcut():
    install = ROOT / "scripts" / "windows" / "install-startup-shortcut.ps1"
    uninstall = ROOT / "scripts" / "windows" / "uninstall-startup-shortcut.ps1"
    start_ui = ROOT / "scripts" / "windows" / "start-ui.ps1"
    start_dev_runner = ROOT / "scripts" / "windows" / "start-dev-runner.ps1"
    setup = ROOT / "scripts" / "windows" / "setup.ps1"
    build = ROOT / "scripts" / "windows" / "build.ps1"

    assert install.exists()
    assert uninstall.exists()
    assert setup.exists()
    assert build.exists()
    install_text = install.read_text(encoding="utf-8")
    uninstall_text = uninstall.read_text(encoding="utf-8")
    start_ui_text = start_ui.read_text(encoding="utf-8")
    start_dev_runner_text = start_dev_runner.read_text(encoding="utf-8")
    setup_text = setup.read_text(encoding="utf-8")
    build_text = build.read_text(encoding="utf-8")

    assert "FastWispr.lnk" in install_text
    assert "start-ui.ps1" in install_text
    assert '$Hotkey = "ctrl+space"' in install_text
    assert "-Hotkey $Hotkey" in install_text
    assert "Startup" in install_text
    assert "FastWispr.lnk" in uninstall_text
    assert "Remove-Item" in uninstall_text
    assert "run-windows-tray" in start_ui_text
    assert "pip install" not in start_ui_text
    assert "pip install" not in start_dev_runner_text
    assert "RandomNumberGenerator" not in start_dev_runner_text
    assert '".[windows,stt,test,packaging]"' in setup_text
    assert "windows-smoke" in setup_text
    assert "PyInstaller" in build_text
    assert "FastWispr" in build_text
    assert "windows-smoke" in build_text
    assert "--hidden-import keyboard" in build_text
    assert "--hidden-import sounddevice" in build_text
    assert "Invoke-External" in setup_text
    assert "Invoke-External" in build_text
    assert "from fastwispr.cli import main" in (ROOT / "src" / "fastwispr" / "__main__.py").read_text(encoding="utf-8")
