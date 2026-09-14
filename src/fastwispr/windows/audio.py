from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from threading import Event
import math
import re
import struct
import time
from typing import Any
import wave

_MIC_SKIP = re.compile(
    r"loopback|stereo mix|what u hear|wave out|mapper|primary sound|hdmi|display audio",
    re.I,
)


def _device_name(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("name") or "").strip()
    try:
        return str(item["name"]).strip()
    except Exception:
        return str(getattr(item, "name", "") or "").strip()


def _device_int(item: Any, key: str) -> int:
    try:
        if isinstance(item, dict):
            return int(item.get(key) or 0)
        return int(item[key] or 0)
    except Exception:
        return 0


def _canon_device_name(name: str) -> str:
    text = re.sub(r"\s+", " ", name.strip().lower())
    text = re.sub(r"^\[\w+]\s*", "", text)
    if re.search(r"headset|headphone|airpods|hands-free|bluetooth", text):
        inner = re.search(r"\(([^)]+)\)", text)
        if inner:
            core = re.sub(r"\s*(hands-free.*|ag audio|stereo)\s*$", "", inner.group(1)).strip()
            if core:
                return core
    return text


def _is_capture_name(name: str) -> bool:
    if not name or _MIC_SKIP.search(name):
        return False
    if re.search(r"\bspeakers?\b", name, re.I) and not re.search(r"mic|microphone|headset", name, re.I):
        return False
    return True


def _wasapi_index(sd: Any) -> int | None:
    try:
        for index, api in enumerate(sd.query_hostapis()):
            label = str(api.get("name") if isinstance(api, dict) else api["name"]).lower()
            if "wasapi" in label:
                return index
    except Exception:
        return None
    return None


def list_input_devices(sd_module: Any | None = None) -> list[str]:
    try:
        sd = sd_module or __import__("sounddevice")
        devices = list(sd.query_devices())
    except Exception:
        return []
    prefer = _wasapi_index(sd)
    wasapi: list[Any] = []
    other: list[Any] = []
    for item in devices:
        if prefer is not None and _device_int(item, "hostapi") == prefer:
            wasapi.append(item)
        else:
            other.append(item)
    return _pick_capture_devices(wasapi + other)


def _pick_capture_devices(devices: list[Any]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for item in devices:
        if _device_int(item, "max_input_channels") <= 0:
            continue
        name = _device_name(item)
        if not _is_capture_name(name):
            continue
        key = _canon_device_name(name)
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names


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
    def __init__(self, sample_rate: int = 16000, channels: int = 1, sd_module: Any | None = None, device: str | None = None):
        if sd_module is None:
            try:
                sd_module = __import__("sounddevice")
            except ImportError as exc:
                raise RuntimeError("Install Windows audio support with: python -m pip install -e '.[windows]'") from exc
        self.sd: Any = sd_module
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device or None

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
            device=self.device,
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
