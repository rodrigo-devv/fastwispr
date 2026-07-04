from pathlib import Path
from threading import Thread
import wave

from fastwispr.controller import DictationController
from fastwispr.db import Store
from fastwispr.stt import TranscriptionResult


class FakeRecorder:
    def record_seconds(self, output_path: str | Path, seconds: float) -> Path:
        return write_wav(Path(output_path), [1000, -1000] * max(1, int(16000 * seconds / 2)))


class FakeStt:
    def __init__(self, text: str = "um meet at five actually six"):
        self.text = text
        self.calls = 0

    def transcribe(self, audio_path: str | Path) -> str:
        self.calls += 1
        return self.text


class FakeResultStt:
    def __init__(self):
        self.calls = 0

    def transcribe_result(self, audio_path: str | Path) -> TranscriptionResult:
        self.calls += 1
        return TranscriptionResult(text="would you like to learn more about the project", language="en", language_probability=0.94)


class FakeInjector:
    def __init__(self):
        self.pasted = ""
        self.calls = 0

    def paste_text(self, text: str) -> None:
        self.calls += 1
        self.pasted = text


def write_wav(path: Path, samples: list[int], sample_rate: int = 16000) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(sample_rate)
        frames = b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples)
        fh.writeframes(frames)
    return path


def latest_event(store: Store):
    return store.conn.execute("SELECT * FROM dictation_events ORDER BY id DESC LIMIT 1").fetchone()


def test_controller_pastes_final_text_without_storing_raw_by_default(tmp_path: Path):
    injector = FakeInjector()
    with Store(tmp_path / "fastwispr.sqlite3") as store:
        controller = DictationController(FakeRecorder(), FakeStt(), injector, store, min_record_seconds=0.0, min_audio_rms=0.0)

        final = controller.dictate_once(seconds=0.01)

        row = latest_event(store)
        assert final == "Meet at six."
        assert injector.pasted == "Meet at six."
        assert row["raw_transcript"] is None
        assert row["final_text"] == "Meet at six."


def test_controller_processes_existing_audio_path(tmp_path: Path):
    injector = FakeInjector()
    audio_path = write_wav(tmp_path / "dictation.wav", [1000, -1000] * 8000)

    with Store(tmp_path / "fastwispr.sqlite3") as store:
        controller = DictationController(FakeRecorder(), FakeStt(), injector, store, min_record_seconds=0.0, min_audio_rms=0.0)

        final = controller.finish_audio(audio_path)

        assert final == "Meet at six."
        assert injector.pasted == "Meet at six."


def test_controller_can_finish_audio_from_worker_thread(tmp_path: Path):
    injector = FakeInjector()
    audio_path = write_wav(tmp_path / "dictation.wav", [1000, -1000] * 8000)

    with Store(tmp_path / "fastwispr.sqlite3") as store:
        controller = DictationController(FakeRecorder(), FakeStt(), injector, store, min_record_seconds=0.0, min_audio_rms=0.0)
        results: list[str] = []
        errors: list[BaseException] = []

        def target() -> None:
            try:
                results.append(controller.finish_audio(audio_path))
            except BaseException as exc:
                errors.append(exc)

        thread = Thread(target=target)
        thread.start()
        thread.join(timeout=5)

        assert not thread.is_alive()
        assert errors == []
        assert results == ["Meet at six."]
        assert injector.pasted == "Meet at six."


def test_controller_skips_recordings_shorter_than_min_duration(tmp_path: Path):
    injector = FakeInjector()
    stt = FakeStt()
    audio_path = write_wav(tmp_path / "short.wav", [1000, -1000] * 1600)

    with Store(tmp_path / "fastwispr.sqlite3") as store:
        controller = DictationController(FakeRecorder(), stt, injector, store, min_record_seconds=0.5, min_audio_rms=0.0)

        final = controller.finish_audio(audio_path)

        row = latest_event(store)
        assert final == ""
        assert stt.calls == 0
        assert injector.calls == 0
        assert row["skipped_reason"] == "too_short"
        assert 190 <= row["audio_duration_ms"] <= 210


def test_controller_skips_silence_before_stt(tmp_path: Path):
    injector = FakeInjector()
    stt = FakeStt()
    audio_path = write_wav(tmp_path / "silent.wav", [0] * 16000)

    with Store(tmp_path / "fastwispr.sqlite3") as store:
        controller = DictationController(FakeRecorder(), stt, injector, store, min_record_seconds=0.1, min_audio_rms=0.003)

        final = controller.finish_audio(audio_path)

        row = latest_event(store)
        assert final == ""
        assert stt.calls == 0
        assert injector.calls == 0
        assert row["skipped_reason"] == "silence"
        assert row["audio_rms"] == 0.0


def test_controller_skips_invalid_audio_before_stt(tmp_path: Path):
    injector = FakeInjector()
    stt = FakeStt()
    audio_path = tmp_path / "broken.wav"
    audio_path.write_bytes(b"not a wav")

    with Store(tmp_path / "fastwispr.sqlite3") as store:
        controller = DictationController(FakeRecorder(), stt, injector, store, min_record_seconds=0.0, min_audio_rms=0.0)

        final = controller.finish_audio(audio_path)

        row = latest_event(store)
        assert final == ""
        assert stt.calls == 0
        assert injector.calls == 0
        assert row["skipped_reason"] == "invalid_audio"


def test_controller_logs_language_audio_and_latency_metrics(tmp_path: Path):
    injector = FakeInjector()
    stt = FakeResultStt()
    audio_path = write_wav(tmp_path / "voice.wav", [2000, -2000] * 8000)

    with Store(tmp_path / "fastwispr.sqlite3") as store:
        controller = DictationController(FakeRecorder(), stt, injector, store, min_record_seconds=0.1, min_audio_rms=0.003)

        final = controller.finish_audio(audio_path)

        row = latest_event(store)
        assert "project" in final.lower()
        assert row["language"] == "en"
        assert row["language_probability"] == 0.94
        assert row["stt_latency_ms"] >= 0
        assert row["latency_ms"] >= row["stt_latency_ms"]
        assert row["audio_duration_ms"] == 1000
        assert row["audio_rms"] > 0.05
        assert row["audio_peak"] > 0.05
        assert row["skipped_reason"] is None
