from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import tomllib
from typing import Any


@dataclass(frozen=True)
class Config:
    db_path: Path
    hotkey: str = "ctrl+space"
    hold_button: str = "xbutton1"
    activation_trigger: str = "keyboard"
    activation_mode: str = "toggle"
    stt_provider: str = "faster-whisper"
    stt_model: str = "small"
    stt_language: str = "pt-en"
    stt_device: str = "cpu"
    stt_compute_type: str = "int8"
    min_record_seconds: float = 0.35
    min_audio_rms: float = 0.003
    store_audio: bool = False
    store_raw_transcripts: bool = False
    restore_clipboard: bool = True


def default_data_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "FastWispr"
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "fastwispr"


def default_config_path() -> Path:
    return default_data_dir() / "config.toml"


def resolve_config_path(path: str | Path | None = None) -> Path:
    return Path(path).expanduser() if path else default_config_path()


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"Config section {name!r} must be a table")
    return value


def _read_bool(section: str, option: str, value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ValueError(f"Config value {section}.{option} must be boolean")


def load_config(path: str | Path | None = None) -> Config:
    config_path = resolve_config_path(path)
    data: dict[str, Any] = {}
    if config_path.exists():
        # Windows PowerShell 5.1 `Set-Content -Encoding utf8` writes a UTF-8 BOM.
        # `tomllib.load()` rejects that at column 1, so read as utf-8-sig.
        data = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))

    storage = _section(data, "storage")
    hotkeys = _section(data, "hotkeys")
    activation = _section(data, "activation")
    stt = _section(data, "stt")
    dictation = _section(data, "dictation")
    privacy = _section(data, "privacy")
    injection = _section(data, "injection")

    db_raw = storage.get("db_path")
    db_path = Path(db_raw).expanduser() if db_raw else default_data_dir() / "fastwispr.sqlite3"
    defaults = Config(db_path=db_path)

    return Config(
        db_path=db_path,
        hotkey=str(hotkeys.get("dictate_toggle", defaults.hotkey)),
        hold_button=str(hotkeys.get("hold_button", defaults.hold_button)),
        activation_trigger=str(activation.get("trigger", defaults.activation_trigger)),
        activation_mode=str(activation.get("mode", defaults.activation_mode)),
        stt_provider=str(stt.get("provider", defaults.stt_provider)),
        stt_model=str(stt.get("model", defaults.stt_model)),
        stt_language=str(stt.get("language", defaults.stt_language)),
        stt_device=str(stt.get("device", defaults.stt_device)),
        stt_compute_type=str(stt.get("compute_type", defaults.stt_compute_type)),
        min_record_seconds=float(dictation.get("min_record_seconds", defaults.min_record_seconds)),
        min_audio_rms=float(dictation.get("min_audio_rms", defaults.min_audio_rms)),
        store_audio=_read_bool("privacy", "store_audio", privacy.get("store_audio", defaults.store_audio)),
        store_raw_transcripts=_read_bool(
            "privacy",
            "store_raw_transcripts",
            privacy.get("store_raw_transcripts", defaults.store_raw_transcripts),
        ),
        restore_clipboard=_read_bool("injection", "restore_clipboard", injection.get("restore_clipboard", defaults.restore_clipboard)),
    )
