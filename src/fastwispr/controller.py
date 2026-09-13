from __future__ import annotations

from pathlib import Path
import tempfile
import time
from typing import Protocol, cast

from .audio_stats import AudioStats, analyze_wav
from .db import Store
from .pipeline import process_text_with_store
from .stt import TranscriptionResult


class Recorder(Protocol):
    def record_seconds(self, output_path: str | Path, seconds: float) -> Path:
        ...


class Transcriber(Protocol):
    def transcribe(self, audio_path: str | Path) -> str:
        ...


class Injector(Protocol):
    def paste_text(self, text: str) -> None:
        ...


class DictationController:
    def __init__(
        self,
        recorder: Recorder,
        transcriber: Transcriber,
        injector: Injector,
        store: Store,
        store_raw_transcripts: bool = False,
        min_record_seconds: float = 0.35,
        min_audio_rms: float = 0.003,
    ):
        self.recorder = recorder
        self.transcriber = transcriber
        self.injector = injector
        self.store = store
        self.store_raw_transcripts = store_raw_transcripts
        self.min_record_seconds = min_record_seconds
        self.min_audio_rms = min_audio_rms
        self.last_paste_ok = True
        self.last_event_id: int | None = None

    def dictate_once(self, seconds: float = 5.0, app_name: str | None = None) -> str:
        started = time.monotonic()
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = self.recorder.record_seconds(Path(tmpdir) / "dictation.wav", seconds)
            return self.finish_audio(audio_path, app_name=app_name, started=started)

    def finish_audio(self, audio_path: str | Path, app_name: str | None = None, started: float | None = None) -> str:
        started = time.monotonic() if started is None else started
        stats = analyze_wav(audio_path)
        if not stats.valid:
            self.last_paste_ok = False
            return ""
        if stats.duration_seconds < self.min_record_seconds:
            self.last_paste_ok = False
            return ""
        if stats.rms_level < self.min_audio_rms:
            self.last_paste_ok = False
            return ""

        stt_started = time.monotonic()
        result = self._transcribe(audio_path)
        stt_latency_ms = int((time.monotonic() - stt_started) * 1000)
        raw = result.text
        final = process_text_with_store(raw, self.store, app_name).final
        if not final.strip():
            self.last_paste_ok = False
            return ""

        latency_ms = int((time.monotonic() - started) * 1000)
        # Persist first so a paste failure never loses the transcript.
        self.last_event_id = self.store.record_dictation_event(
            raw_transcript=raw if self.store_raw_transcripts else None,
            final_text=final,
            latency_ms=latency_ms,
            stt_latency_ms=stt_latency_ms,
            audio_duration_ms=stats.duration_ms,
            language=result.language,
            language_probability=result.language_probability,
            audio_rms=stats.rms_level,
            audio_peak=stats.peak_level,
            app_name=app_name,
            stt_model=getattr(self.transcriber, "model_name", None),
        )
        try:
            self.injector.paste_text(final)
            self.last_paste_ok = True
        except Exception:
            self.last_paste_ok = False
        return final

    def last_completed_text(self) -> str:
        event = self.store.latest_completed_event()
        return event.final_text if event else ""

    def copy_last_transcript(self) -> str:
        text = self.last_completed_text()
        if not text:
            return ""
        copy_text = getattr(self.injector, "copy_text", None)
        if callable(copy_text):
            copy_text(text)
        else:
            self.injector.paste_text(text)
        return text

    def retry_paste(self, text: str | None = None) -> str:
        payload = text if text is not None else self.last_completed_text()
        if not payload:
            return ""
        try:
            self.injector.paste_text(payload)
            self.last_paste_ok = True
        except Exception:
            self.last_paste_ok = False
        return payload

    def _transcribe(self, audio_path: str | Path) -> TranscriptionResult:
        transcribe_result = getattr(self.transcriber, "transcribe_result", None)
        if callable(transcribe_result):
            return cast(TranscriptionResult, transcribe_result(audio_path))
        return TranscriptionResult(text=self.transcriber.transcribe(audio_path))

    def _record_skipped_event(
        self,
        reason: str,
        stats: AudioStats,
        app_name: str | None,
        started: float,
        *,
        stt_latency_ms: int | None = None,
    ) -> None:
        self.store.record_dictation_event(
            raw_transcript=None,
            final_text="",
            latency_ms=int((time.monotonic() - started) * 1000),
            stt_latency_ms=stt_latency_ms,
            audio_duration_ms=stats.duration_ms,
            audio_rms=stats.rms_level,
            audio_peak=stats.peak_level,
            skipped_reason=reason,
            app_name=app_name,
            stt_model=getattr(self.transcriber, "model_name", None),
        )