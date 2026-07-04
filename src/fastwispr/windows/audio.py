from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from threading import Event
import math
import struct
import time
from typing import Any
import wave


def int16_rms_level(data: bytes) -> float:
    if len(data) < 2:
        return 0.0
    sample_count = len(data) // 2
    total = 0
    for (sample,) in struct.iter_unpack("<h", data[: sample_count * 2]):
        total += sample * sample
    if total == 0:
        return 0.0
    return min(1.0, math.sqrt(total / sample_count) / 32767.0)


class SounddeviceRecorder:
    def __init__(self, sample_rate: int = 16000, channels: int = 1, sd_module: Any | None = None):
        if sd_module is None:
            try:
                sd_module = __import__("sounddevice")
            except ImportError as exc:
                raise RuntimeError("Install Windows audio support with: python -m pip install -e '.[windows]'") from exc
        self.sd: Any = sd_module
        self.sample_rate = sample_rate
        self.channels = channels

    def record_seconds(self, output_path: str | Path, seconds: float) -> Path:
        stop_event = Event()

        def stop_after_delay() -> None:
            if hasattr(self.sd, "sleep"):
                self.sd.sleep(int(seconds * 1000))
            else:
                time.sleep(seconds)
            stop_event.set()

        return self._record(output_path, stop_event, stop_after_delay=stop_after_delay)

    def record_until_stopped(
        self,
        output_path: str | Path,
        stop_event: Event,
        *,
        level_callback: Callable[[float], None] | None = None,
        poll_interval_seconds: float = 0.02,
    ) -> Path:
        return self._record(output_path, stop_event, level_callback=level_callback, poll_interval_seconds=poll_interval_seconds)

    def _record(
        self,
        output_path: str | Path,
        stop_event: Event,
        *,
        level_callback: Callable[[float], None] | None = None,
        poll_interval_seconds: float = 0.02,
        stop_after_delay: Callable[[], None] | None = None,
    ) -> Path:
        output = Path(output_path)
        frames = bytearray()

        def callback(indata: Any, frame_count: int, time_info: object, status: object) -> None:
            chunk = bytes(indata)
            frames.extend(chunk)
            if level_callback is not None:
                level_callback(int16_rms_level(chunk))

        with self.sd.RawInputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            callback=callback,
        ):
            if stop_after_delay is not None:
                stop_after_delay()
            else:
                while not stop_event.is_set():
                    if hasattr(self.sd, "sleep"):
                        self.sd.sleep(int(poll_interval_seconds * 1000))
                    else:
                        time.sleep(poll_interval_seconds)

        output.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output), "wb") as fh:
            fh.setnchannels(self.channels)
            fh.setsampwidth(2)
            fh.setframerate(self.sample_rate)
            fh.writeframes(bytes(frames))
        return output
