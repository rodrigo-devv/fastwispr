from __future__ import annotations

import sys
from pathlib import Path

from ..config import Config, default_config_path
from ..controller import DictationController
from ..db import Store
from ..stt import make_stt
from ..windows.audio import SounddeviceRecorder
from ..windows.hotkeys import KeyboardHotkeyListener
from ..windows.hold_to_talk import HoldToTalkDictationApp
from ..windows.injector import ClipboardPasteInjector
from .hub import AppShell, attach_tray
from .overlay import QtRecordingOverlay

try:
    from PySide6.QtWidgets import QApplication
except ImportError as exc:  # pragma: no cover - optional extra
    raise RuntimeError("Install the GUI extra with: python -m pip install -e '.[gui]'") from exc


def run_qt_app(config: Config, *, config_path: Path | None = None, autostart: bool = True) -> None:
    """Run hub + overlay + dictation in one Qt process. STT stays off the GUI thread."""
    app = QApplication.instance() or QApplication(sys.argv)
    store = Store(config.db_path)
    recorder = SounddeviceRecorder()
    controller = DictationController(
        recorder=recorder,
        transcriber=make_stt(
            config.stt_provider,
            config.stt_model,
            config.stt_device,
            config.stt_compute_type,
            config.stt_language,
        ),
        injector=ClipboardPasteInjector(restore_clipboard=config.restore_clipboard),
        store=store,
        store_raw_transcripts=config.store_raw_transcripts,
        min_record_seconds=config.min_record_seconds,
        min_audio_rms=config.min_audio_rms,
    )
    overlay = QtRecordingOverlay(theme_preference=config.ui_theme)
    resolved_config = config_path or default_config_path()
    hub = AppShell(config, store, resolved_config, controller, overlay)

    def open_history() -> None:
        hub.open_hub()
        hub.show_page("history")

    overlay.set_error_handler(open_history)

    def retry_from_pill() -> None:
        if controller.last_completed_text():
            controller.retry_paste()
        else:
            open_history()

    overlay.set_retry_handler(retry_from_pill)

    listener = KeyboardHotkeyListener(config.hotkey)
    dictation = HoldToTalkDictationApp(
        controller=controller,
        recorder=recorder,
        overlay=overlay,
        listener=listener,
        activation_mode="toggle",
    )
    paused = {"value": False}

    def start_recording() -> None:
        dictation.post(dictation.toggle_recording)

    def pause_hotkeys() -> None:
        if paused["value"]:
            dictation.start()
            paused["value"] = False
        else:
            listener.stop()
            paused["value"] = True

    original_finish = dictation._finish_recording

    def finish_and_notify() -> None:
        original_finish()
        if getattr(controller, "last_paste_ok", True) is False and controller.last_completed_text():
            hub.show_paste_failed()

    dictation._finish_recording = finish_and_notify  # type: ignore[method-assign]
    attach_tray(hub, on_start=start_recording, on_pause=pause_hotkeys)
    dictation.start()
    if autostart:
        hub.open_hub()
    try:
        app.exec()
    finally:
        dictation.shutdown()
        store.close()
