from __future__ import annotations

from collections.abc import Sequence
from threading import Thread
from typing import Any

START_SEQUENCE = ((880, 45), (1175, 65))
STOP_SEQUENCE = ((660, 55), (440, 65))


def _load_winsound() -> Any | None:
    try:
        return __import__("winsound")
    except ImportError:
        return None


def _play_sequence(sequence: Sequence[tuple[int, int]], winsound_module: Any | None = None) -> bool:
    winsound = winsound_module if winsound_module is not None else _load_winsound()
    if winsound is None:
        return False
    try:
        for frequency, duration in sequence:
            winsound.Beep(frequency, duration)
    except Exception:
        return False
    return True


def _play(sequence: Sequence[tuple[int, int]], *, winsound_module: Any | None = None, threaded: bool = True) -> bool:
    if not threaded:
        return _play_sequence(sequence, winsound_module)
    Thread(target=_play_sequence, args=(sequence, winsound_module), name="fastwispr-sound", daemon=True).start()
    return True


def play_recording_started(*, winsound_module: Any | None = None, threaded: bool = True) -> bool:
    return _play(START_SEQUENCE, winsound_module=winsound_module, threaded=threaded)


def play_recording_stopped(*, winsound_module: Any | None = None, threaded: bool = True) -> bool:
    return _play(STOP_SEQUENCE, winsound_module=winsound_module, threaded=threaded)
