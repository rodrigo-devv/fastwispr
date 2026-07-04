from pathlib import Path
import logging

from fastwispr.logging_setup import app_log_path, configure_file_logging


def test_app_log_path_uses_appdata_on_windows(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))

    assert app_log_path() == tmp_path / "Roaming" / "FastWispr" / "fastwispr.log"


def test_configure_file_logging_creates_log_file(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))

    log_path = configure_file_logging(force=True)
    logging.getLogger("fastwispr.test").info("hello log")
    logging.shutdown()

    assert log_path.exists()
    assert "hello log" in log_path.read_text(encoding="utf-8")
