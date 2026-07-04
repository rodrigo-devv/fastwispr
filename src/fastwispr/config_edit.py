from __future__ import annotations

from pathlib import Path
import tomllib
from typing import Any


SUPPORTED_CONFIG_KEYS: dict[str, set[str]] = {
    "storage": {"db_path"},
    "hotkeys": {"dictate_toggle", "hold_button"},
    "activation": {"trigger", "mode"},
    "stt": {"provider", "model", "language", "device", "compute_type"},
    "dictation": {"min_record_seconds", "min_audio_rms"},
    "privacy": {"store_audio", "store_raw_transcripts"},
    "injection": {"restore_clipboard"},
}

CONFIG_SECTION_ORDER = ["storage", "hotkeys", "activation", "stt", "dictation", "privacy", "injection"]


def set_config_value(path: Path, key: str, raw_value: str) -> None:
    data = read_config_dict(path)
    section, option = split_config_key(key)
    value = parse_config_value(section, option, raw_value)
    data.setdefault(section, {})[option] = value
    write_config_dict(path, data)


def merge_config_dict(path: Path, updates: dict[str, Any]) -> None:
    data = read_config_dict(path)
    for section, values in updates.items():
        if not isinstance(values, dict):
            raise ValueError(f"Config section {section!r} must be an object")
        for option, value in values.items():
            parse_config_value(section, option, str(value).lower() if isinstance(value, bool) else str(value))
            data.setdefault(section, {})[option] = value
    write_config_dict(path, data)


def write_config_dict(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config_dict_to_toml(data), encoding="utf-8")


def read_config_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8-sig"))


def split_config_key(key: str) -> tuple[str, str]:
    parts = key.split(".", 1)
    if len(parts) != 2 or not all(parts):
        raise SystemExit("Config key must be section.option, e.g. stt.language")
    return parts[0], parts[1]


def parse_config_value(section: str, option: str, raw_value: str) -> str | float | bool:
    if option not in SUPPORTED_CONFIG_KEYS.get(section, set()):
        raise SystemExit(f"Unsupported config key: {section}.{option}")
    if section == "dictation":
        return float(raw_value)
    if section in {"privacy", "injection"}:
        return parse_bool(raw_value)
    return raw_value


def parse_bool(raw_value: str) -> bool:
    value = raw_value.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise SystemExit(f"Expected boolean value, got {raw_value!r}")


def config_dict_to_toml(data: dict[str, Any]) -> str:
    lines: list[str] = []
    for section in CONFIG_SECTION_ORDER + sorted(set(data) - set(CONFIG_SECTION_ORDER)):
        values = data.get(section)
        if not isinstance(values, dict) or not values:
            continue
        if lines:
            lines.append("")
        lines.append(f"[{section}]")
        for key, value in values.items():
            lines.append(f"{key} = {toml_value(value)}")
    return "\n".join(lines) + "\n"


def toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return f"{value:g}"
    return quote_string(str(value))


def quote_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
