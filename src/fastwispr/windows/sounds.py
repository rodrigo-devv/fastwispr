from __future__ import annotations

from collections.abc import Callable, Sequence
from io import BytesIO
import math
from threading import Thread
from typing import Any
import wave

Cue = Sequence[tuple[int, int]]

START_CUE: tuple[tuple[int, int], ...] = ((720, 32), (960, 42))
STOP_CUE: tuple[tuple[int, int], ...] = ((880, 30), (587, 48))
DEFAULT_SAMPLE_RATE = 22_050
DEFAULT_VOLUME = 0.13
FADE_MS = 6


def _load_winsound() -> Any | None:
    try:
        return __import__("winsound")
    except ImportError:
        return None


def build_cue_wav(
    cue: Cue,
    *,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    volume: float = DEFAULT_VOLUME,
    fade_ms: int = FADE_MS,
) -> bytes:
    samples: list[int] = []
    amplitude = int(32767 * max(0.0, min(volume, 1.0)))
    fade_samples = max(1, int(sample_rate * fade_ms / 1000))

    for frequency, duration_ms in cue:
        tone_samples = max(1, int(sample_rate * duration_ms / 1000))
        for index in range(tone_samples):
            fade_in = min(1.0, index / fade_samples)
            fade_out = min(1.0, (tone_samples - 1 - index) / fade_samples)
            envelope = min(fade_in, fade_out)
            radians = 2 * math.pi * frequency * (index / sample_rate)
            samples.append(int(amplitude * envelope * math.sin(radians)))

    payload = b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples)
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(payload)
    return buffer.getvalue()


def _play_wav_bytes(wav_bytes: bytes, winsound_module: Any | None = None) -> bool:
    winsound = winsound_module if winsound_module is not None else _load_winsound()
    if winsound is None:
        return False
    play_sound = getattr(winsound, "PlaySound", None)
    if play_sound is None:
        return False
    flags = getattr(winsound, "SND_MEMORY", 0x0004) | getattr(winsound, "SND_NODEFAULT", 0x0002)
    try:
        play_sound(wav_bytes, flags)
    except Exception:
        return False
    return True


def _play(cue: Cue, *, winsound_module: Any | None = None, threaded: bool = True) -> bool:
    winsound = winsound_module if winsound_module is not None else _load_winsound()
    if winsound is None:
        return False
    wav_bytes = build_cue_wav(cue)
    if not threaded:
        return _play_wav_bytes(wav_bytes, winsound)
    Thread(target=_play_wav_bytes, args=(wav_bytes, winsound), name="fastwispr-sound", daemon=True).start()
    return True


def play_recording_started(*, winsound_module: Any | None = None, threaded: bool = True) -> bool:
    return _play(START_CUE, winsound_module=winsound_module, threaded=threaded)


def play_recording_stopped(*, winsound_module: Any | None = None, threaded: bool = True) -> bool:
    return _play(STOP_CUE, winsound_module=winsound_module, threaded=threaded)


def sound_smoke(*, winsound_module: Any | None = None, pause_seconds: float = 0.08) -> bool:
    sleep: Callable[[float], None]
    from time import sleep as sleep

    if not play_recording_started(winsound_module=winsound_module, threaded=False):
        return False
    sleep(pause_seconds)
    return play_recording_stopped(winsound_module=winsound_module, threaded=False)
