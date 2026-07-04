from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import time

import fastwispr.windows.hold_to_talk as hold_to_talk
from fastwispr.windows.hold_to_talk import HoldToTalkDictationApp


class FakeRoot:
    def after(self, delay_ms: int, callback):
        return None


class FakeOverlay:
    def __init__(self):
        self.root = FakeRoot()
        self.states = []
        self.levels = []
        self.hidden = False

    def set_level(self, level: float) -> None:
        self.levels.append(level)

    def set_state(self, state: str) -> None:
        self.states.append(state)

    def hide(self) -> None:
        self.hidden = True

    def run(self) -> None:
        return None


class FakeRecorder:
    def record_until_stopped(self, output_path: Path, stop_event: Event, *, level_callback=None):
        if level_callback is not None:
            level_callback(0.2)
        stop_event.wait(timeout=1)
        output_path.write_bytes(b"fake wav")
        return output_path


class HangingRecorder:
    def __init__(self):
        self.started = Event()

    def record_until_stopped(self, output_path: Path, stop_event: Event, *, level_callback=None):
        self.started.set()
        time.sleep(0.2)
        output_path.write_bytes(b"late wav")
        return output_path


class FakeController:
    def __init__(self, final: str = "ok"):
        self.final = final
        self.calls = 0

    def finish_audio(self, audio_path: Path, *, started: float):
        assert audio_path.exists()
        self.calls += 1
        return self.final


class FakeListener:
    def start(self, on_down, on_up):
        self.on_down = on_down
        self.on_up = on_up

    def stop(self):
        pass


def wait_for_finish(app: HoldToTalkDictationApp) -> None:
    if app.record_thread is not None:
        app.record_thread.join(timeout=1)
    if getattr(app, "finish_thread", None) is not None:
        app.finish_thread.join(timeout=1)
    assert not app.processing


def test_hold_to_talk_plays_start_and_stop_sounds(monkeypatch):
    calls = []
    monkeypatch.setattr(hold_to_talk, "play_recording_started", lambda: calls.append("start"))
    monkeypatch.setattr(hold_to_talk, "play_recording_stopped", lambda: calls.append("stop"))
    app = HoldToTalkDictationApp(FakeController(), FakeRecorder(), FakeOverlay(), FakeListener())

    app.start_recording()
    app.stop_recording()
    wait_for_finish(app)

    assert calls[:2] == ["start", "stop"]


def test_stop_sound_plays_after_recorder_stop_is_signaled(monkeypatch):
    calls = []
    app = HoldToTalkDictationApp(FakeController(), FakeRecorder(), FakeOverlay(), FakeListener())
    monkeypatch.setattr(hold_to_talk, "play_recording_started", lambda: calls.append(("start", False)))
    monkeypatch.setattr(hold_to_talk, "play_recording_stopped", lambda: calls.append(("stop", app.stop_event.is_set())))

    app.start_recording()
    app.stop_recording()
    wait_for_finish(app)

    assert ("stop", True) in calls


def test_hanging_recorder_does_not_transcribe_partial_audio(monkeypatch):
    monkeypatch.setattr(hold_to_talk, "play_recording_started", lambda: None)
    monkeypatch.setattr(hold_to_talk, "play_recording_stopped", lambda: None)
    recorder = HangingRecorder()
    controller = FakeController()
    overlay = FakeOverlay()
    app = HoldToTalkDictationApp(
        controller,
        recorder,
        overlay,
        FakeListener(),
        record_join_timeout_seconds=0.01,
    )

    app.start_recording()
    assert recorder.started.wait(timeout=1)
    app.stop_recording()
    wait_for_finish(app)
    app._drain_events()

    assert controller.calls == 0
    assert "error" in overlay.states


def test_toggle_mode_starts_and_stops_on_mouse_down(monkeypatch):
    monkeypatch.setattr(hold_to_talk, "play_recording_started", lambda: None)
    monkeypatch.setattr(hold_to_talk, "play_recording_stopped", lambda: None)
    listener = FakeListener()
    app = HoldToTalkDictationApp(FakeController(), FakeRecorder(), FakeOverlay(), listener, activation_mode="toggle")
    app.run()

    listener.on_down()
    app._drain_events()
    assert app.recording is True

    listener.on_up()
    app._drain_events()
    assert app.recording is True

    listener.on_down()
    app._drain_events()
    wait_for_finish(app)

    assert app.recording is False


def test_skipped_empty_dictation_hides_overlay_without_paste_state(monkeypatch):
    monkeypatch.setattr(hold_to_talk, "play_recording_started", lambda: None)
    monkeypatch.setattr(hold_to_talk, "play_recording_stopped", lambda: None)
    overlay = FakeOverlay()
    app = HoldToTalkDictationApp(FakeController(final=""), FakeRecorder(), overlay, FakeListener())

    app.start_recording()
    app.stop_recording()
    wait_for_finish(app)
    app._drain_events()

    assert overlay.hidden is True
    assert "pasting" not in overlay.states
