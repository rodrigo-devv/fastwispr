from __future__ import annotations

from .config import Config
from .controller import DictationController
from .db import Store
from .stt import make_stt


def run_windows_app(config: Config) -> None:
    from .windows.audio import SounddeviceRecorder
    from .windows.hotkeys import KeyboardHotkeyListener
    from .windows.hold_to_talk import HoldToTalkDictationApp
    from .windows.injector import ClipboardPasteInjector
    from .windows.mouse_buttons import XButtonHoldListener
    from .windows.overlay import FloatingAudioOverlay

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
    if config.activation_trigger == "keyboard":
        if config.activation_mode != "toggle":
            raise RuntimeError("Keyboard trigger supports activation.mode=toggle. Use activation.trigger=mouse for hold mode.")
        listener = KeyboardHotkeyListener(config.hotkey)
        trigger_label = config.hotkey
    elif config.activation_trigger == "mouse":
        listener = XButtonHoldListener(config.hold_button)
        trigger_label = config.hold_button
    else:
        raise RuntimeError("activation.trigger must be keyboard or mouse")

    app = HoldToTalkDictationApp(
        controller=controller,
        recorder=recorder,
        overlay=FloatingAudioOverlay(),
        listener=listener,
        activation_mode=config.activation_mode,
    )
    if config.activation_mode == "toggle":
        print(f"Press {trigger_label} to start. Press again to stop/transcribe/paste. Press Ctrl+C to exit.")
    else:
        print(f"Hold {trigger_label} to dictate. Release to transcribe and paste. Press Ctrl+C to exit.")
    try:
        app.run()
    finally:
        store.close()
