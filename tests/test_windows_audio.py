from __future__ import annotations

from pathlib import Path
from threading import Event
import wave

from fastwispr.windows.audio import SounddeviceRecorder


class FakeStream:
    def __init__(self, callback, stop_after_first_callback: Event | None = None):
        self.callback = callback
        self.stop_after_first_callback = stop_after_first_callback

    def __enter__(self):
        self.callback(b"\x01\x00\x02\x00", 2, None, None)
        if self.stop_after_first_callback is not None:
            self.stop_after_first_callback.set()
        self.callback(b"\x03\x00\x04\x00", 2, None, None)
        return self

    def __exit__(self, *exc):
        return None


class FakeSoundDevice:
    def __init__(self, stop_event: Event | None = None):
        self.slept_ms = None
        self.stop_event = stop_event

    def RawInputStream(self, **kwargs):
        assert kwargs["samplerate"] == 16000
        assert kwargs["channels"] == 1
        assert kwargs["dtype"] == "int16"
        return FakeStream(kwargs["callback"], self.stop_event)

    def sleep(self, ms: int):
        self.slept_ms = ms


def test_sounddevice_recorder_uses_raw_stream_without_numpy(tmp_path: Path):
    fake_sd = FakeSoundDevice()
    output = SounddeviceRecorder(sd_module=fake_sd).record_seconds(tmp_path / "sample.wav", 0.25)

    assert fake_sd.slept_ms == 250
    with wave.open(str(output), "rb") as fh:
        assert fh.getnchannels() == 1
        assert fh.getframerate() == 16000
        assert fh.getsampwidth() == 2
        assert fh.readframes(4) == b"\x01\x00\x02\x00\x03\x00\x04\x00"


def test_sounddevice_recorder_records_until_stop_and_reports_level(tmp_path: Path):
    stop_event = Event()
    levels: list[float] = []
    fake_sd = FakeSoundDevice(stop_event)

    output = SounddeviceRecorder(sd_module=fake_sd).record_until_stopped(
        tmp_path / "hold.wav",
        stop_event,
        level_callback=levels.append,
        poll_interval_seconds=0.001,
    )

    assert levels
    assert output.exists()
    with wave.open(str(output), "rb") as fh:
        assert fh.readframes(4) == b"\x01\x00\x02\x00\x03\x00\x04\x00"
