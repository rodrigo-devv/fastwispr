from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import struct
import wave


@dataclass(frozen=True)
class AudioStats:
    valid: bool
    duration_seconds: float
    rms_level: float
    peak_level: float
    frame_count: int

    @property
    def duration_ms(self) -> int:
        return int(round(self.duration_seconds * 1000))


def analyze_wav(path: str | Path) -> AudioStats:
    try:
        with wave.open(str(path), "rb") as fh:
            frame_count = fh.getnframes()
            sample_rate = fh.getframerate() or 1
            sample_width = fh.getsampwidth()
            frames = fh.readframes(frame_count)
    except (OSError, EOFError, wave.Error):
        return AudioStats(False, 0.0, 0.0, 0.0, 0)

    if sample_width != 2 or frame_count <= 0:
        return AudioStats(True, frame_count / sample_rate, 0.0, 0.0, frame_count)

    sample_count = len(frames) // 2
    if sample_count == 0:
        return AudioStats(True, frame_count / sample_rate, 0.0, 0.0, frame_count)

    total = 0
    peak = 0
    for (sample,) in struct.iter_unpack("<h", frames[: sample_count * 2]):
        abs_sample = abs(sample)
        peak = max(peak, abs_sample)
        total += sample * sample

    rms = math.sqrt(total / sample_count) / 32767.0 if total else 0.0
    return AudioStats(
        valid=True,
        duration_seconds=frame_count / sample_rate,
        rms_level=min(1.0, rms),
        peak_level=min(1.0, peak / 32767.0),
        frame_count=frame_count,
    )
