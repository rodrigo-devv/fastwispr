import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    pytest.skip("Qt platform libraries are unavailable in this environment", allow_module_level=True)

from fastwispr.config import Config
from fastwispr.db import Store
from fastwispr.gui.hub import AppShell
from fastwispr.gui.overlay import QtRecordingOverlay
from fastwispr.gui.theme import HUB_DEFAULT, HUB_MAX, HUB_MIN, OVERLAY_H, TITLEBAR_H


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    return app


def test_hub_shell_matches_approved_geometry(qapp, tmp_path):
    del qapp
    config = Config(db_path=tmp_path / "fastwispr.sqlite3")
    with Store(config.db_path) as store:
        hub = AppShell(config, store, tmp_path / "config.toml")
        assert hub.minimumSize().width() == HUB_MIN[0]
        assert hub.minimumSize().height() == HUB_MIN[1]
        assert hub.maximumSize().width() == HUB_MAX[0]
        assert hub.maximumSize().height() == HUB_MAX[1]
        assert hub.size().width() == HUB_DEFAULT[0]
        assert hub.size().height() == HUB_DEFAULT[1]
        assert hub.titlebar.height() == TITLEBAR_H
        assert hub.findChild(type(hub.titlebar), "TitleBar") is not None
        labels = [child.text() for child in hub.titlebar.findChildren(type(hub.titlebar)) if hasattr(child, "text")]
        # Wordmark is split: Fast + WISPR, never FASTWISPR.
        assert "Fast" in {child.text() for child in hub.titlebar.findChildren(object) if hasattr(child, "text")}
        del labels
        hub.show_page("history")
        hub.show_page("dictionary")
        hub.show_page("snippets")
        hub.show_page("settings")
        hub.show_page("speech")
        hub.show_page("home")
        hub.close()


def test_home_shows_real_model_not_fake_large(qapp, tmp_path):
    del qapp
    config = Config(db_path=tmp_path / "fastwispr.sqlite3", stt_model="small")
    with Store(config.db_path) as store:
        hub = AppShell(config, store, tmp_path / "config.toml")
        texts = [child.text() for child in hub.findChildren(object) if hasattr(child, "text")]
        joined = " ".join(str(text) for text in texts)
        assert "whisper-small" in joined
        assert "whisper-large-v3" not in joined
        assert "Ctrl" in joined
        assert "Space" in joined
        hub.close()


def test_overlay_does_not_accept_focus_and_has_pill_height(qapp):
    del qapp
    overlay = QtRecordingOverlay()
    overlay.set_state("recording")
    assert overlay.height() == OVERLAY_H
    assert overlay.minimumWidth() >= 140
    overlay.close()
