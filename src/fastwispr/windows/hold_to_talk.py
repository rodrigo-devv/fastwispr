from __future__ import annotations

from queue import Empty, Queue
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Thread, current_thread
import time
from typing import Callable

from ..controller import DictationController
from .sounds import play_recording_started, play_recording_stopped


class HoldToTalkDictationApp:
    def __init__(
        self,
        controller: DictationController,
        recorder,
        overlay,
        listener,
        *,
        sample_name: str = "dictation.wav",
        activation_mode: str = "hold",
        record_join_timeout_seconds: float = 10.0,
    ):
        if activation_mode not in {"hold", "toggle"}:
            raise ValueError("activation_mode must be hold or toggle")
        self.controller = controller
        self.recorder = recorder
        self.overlay = overlay
        self.listener = listener
        self.sample_name = sample_name
        self.activation_mode = activation_mode
        self.record_join_timeout_seconds = record_join_timeout_seconds
        self.events: Queue[Callable[[], None]] = Queue()
        self.stop_event: Event | None = None
        self.record_thread: Thread | None = None
        self.finish_thread: Thread | None = None
        self.record_error: Exception | None = None
        self.tempdir: TemporaryDirectory[str] | None = None
        self.audio_path: Path | None = None
        self.record_started_at: float | None = None
        self.recording = False
        self.processing = False
        self.shutting_down = False

    def run(self) -> None:
        self.overlay.root.after(25, self._drain_events)
        if self.activation_mode == "toggle":
            self.listener.start(lambda: self.post(self.toggle_recording), lambda: None)
        else:
            self.listener.start(lambda: self.post(self.start_recording), lambda: self.post(self.stop_recording))
        try:
            self.overlay.run()
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        if self.shutting_down:
            return
        self.shutting_down = True
        try:
            self.listener.stop()
        finally:
            if self.stop_event is not None:
                self.stop_event.set()
            if self.record_thread is not None and self.record_thread.is_alive():
                self.record_thread.join(timeout=self.record_join_timeout_seconds)
            if self.finish_thread is not None and self.finish_thread.is_alive() and self.finish_thread is not current_thread():
                self.finish_thread.join(timeout=self.record_join_timeout_seconds)
            if not self._record_thread_alive() and self.tempdir is not None:
                self.tempdir.cleanup()
                self.tempdir = None

    def post(self, callback: Callable[[], None]) -> None:
        self.events.put(callback)

    def _drain_events(self) -> None:
        try:
            while True:
                try:
                    callback = self.events.get_nowait()
                except Empty:
                    break
                try:
                    callback()
                except Exception as exc:  # pragma: no cover - UI callback guard
                    print(f"FastWispr UI callback failed: {exc}")
        finally:
            self.overlay.root.after(25, self._drain_events)

    def start_recording(self) -> None:
        if self.recording or self.processing:
            return
        self.tempdir = TemporaryDirectory(prefix="fastwispr-hold-")
        self.audio_path = Path(self.tempdir.name) / self.sample_name
        self.stop_event = Event()
        self.record_error = None
        self.recording = True
        self.record_started_at = time.monotonic()
        play_recording_started()
        self.overlay.set_level(0.0)
        self.overlay.set_state("recording")
        self.record_thread = Thread(target=self._record_audio, name="fastwispr-record", daemon=True)
        self.record_thread.start()

    def stop_recording(self) -> None:
        if not self.recording or self.stop_event is None:
            return
        self.recording = False
        self.processing = True
        self.stop_event.set()
        play_recording_stopped()
        self.overlay.set_state("processing")
        self.finish_thread = Thread(target=self._finish_recording, name="fastwispr-finish", daemon=True)
        self.finish_thread.start()

    def toggle_recording(self) -> None:
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def _record_audio(self) -> None:
        try:
            if self.audio_path is None or self.stop_event is None:
                return
            self.recorder.record_until_stopped(
                self.audio_path,
                self.stop_event,
                level_callback=lambda level: self.post(lambda level=level: self.overlay.set_level(level)),
            )
        except Exception as exc:  # pragma: no cover - hardware path
            self.record_error = exc
            self.post(lambda: self.overlay.set_state("error"))

    def _finish_recording(self) -> None:
        cleanup_tempdir = True
        try:
            if self.record_thread is not None:
                self.record_thread.join(timeout=self.record_join_timeout_seconds)
                if self.record_thread.is_alive():
                    cleanup_tempdir = False
                    raise TimeoutError("Recorder did not stop in time; skipping partial audio")
            if self.record_error is not None:
                raise self.record_error
            if self.audio_path is None:
                return
            final = self.controller.finish_audio(self.audio_path, started=self.record_started_at or time.monotonic())
            if final.strip():
                self.post(lambda: self._show_pasted(final))
            else:
                self.post(self.overlay.hide)
        except Exception as exc:  # pragma: no cover - hardware/STT path
            print(f"Dictation failed: {exc}")
            self.post(lambda: self.overlay.set_state("error"))
        finally:
            if cleanup_tempdir and self.tempdir is not None:
                self.tempdir.cleanup()
                self.tempdir = None
            self.audio_path = None
            self.record_started_at = None
            self.processing = False

    def _record_thread_alive(self) -> bool:
        return self.record_thread is not None and self.record_thread.is_alive()

    def _show_pasted(self, final: str) -> None:
        self.overlay.set_state("pasting")
        print(f"Pasted {len(final)} characters.")
        self.overlay.root.after(450, self.overlay.hide)
