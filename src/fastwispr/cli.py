from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import tomllib
from typing import Any

from .app import run_windows_app
from .audio_stats import analyze_wav
from .backup import import_backup, write_backup
from .config import Config, load_config, resolve_config_path
from .db import DictationEvent, Store, init_db
from .logging_setup import configure_file_logging
from .pipeline import process_text_with_store
from .stt import make_stt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fastwispr")
    parser.add_argument("--config", help="Path to config.toml")
    sub = parser.add_subparsers(dest="command")

    process = sub.add_parser("process", help="Process typed transcript text")
    process.add_argument("text", nargs="+")

    sub.add_parser("init-db", help="Create the SQLite database")

    add_dict = sub.add_parser("add-dictionary", help="Add or update a dictionary replacement")
    add_dict.add_argument("term")
    add_dict.add_argument("replacement")

    dictionary = sub.add_parser("dictionary", help="Manage dictionary replacements")
    dictionary_sub = dictionary.add_subparsers(dest="dictionary_command")
    dictionary_sub.add_parser("list", help="List dictionary replacements")
    dictionary_add = dictionary_sub.add_parser("add", help="Add or update a dictionary replacement")
    dictionary_add.add_argument("term")
    dictionary_add.add_argument("replacement")
    dictionary_remove = dictionary_sub.add_parser("remove", help="Remove a dictionary replacement")
    dictionary_remove.add_argument("term")

    add_snippet = sub.add_parser("add-snippet", help="Add or update a snippet")
    add_snippet.add_argument("cue")
    add_snippet.add_argument("body")

    transcribe = sub.add_parser("transcribe", help="Transcribe an audio file")
    transcribe.add_argument("audio_path")
    transcribe.add_argument("--provider", default=None)
    transcribe.add_argument("--model", default=None)
    transcribe.add_argument("--language", default=None)
    transcribe.add_argument("--device", default=None)
    transcribe.add_argument("--compute-type", default=None)

    history = sub.add_parser("history", help="Print recent dictation events")
    history.add_argument("--limit", type=int, default=10)
    history.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    history.add_argument("--skipped-only", action="store_true", help="Only show skipped dictations")
    history.add_argument("--language", default=None, help="Only show events for a detected language, e.g. en or pt")

    calibrate = sub.add_parser("calibrate-audio", help="Measure ambient microphone RMS and suggest min_audio_rms")
    calibrate.add_argument("--seconds", type=float, default=5.0)
    calibrate.add_argument("--apply", action="store_true", help="Write suggested threshold to config")

    config = sub.add_parser("config", help="Show or update config.toml")
    config_sub = config.add_subparsers(dest="config_command")
    config_sub.add_parser("show", help="Show effective config")
    config_set = config_sub.add_parser("set", help="Set a config key")
    config_set.add_argument("key")
    config_set.add_argument("value")

    backup = sub.add_parser("backup", help="Export or import config, dictionary, and snippets")
    backup_sub = backup.add_subparsers(dest="backup_command")
    backup_export = backup_sub.add_parser("export", help="Write a portable JSON backup")
    backup_export.add_argument("path")
    backup_import = backup_sub.add_parser("import", help="Import a portable JSON backup")
    backup_import.add_argument("path")

    settings = sub.add_parser("settings", help="Open the Windows settings UI")
    settings_sub = settings.add_subparsers(dest="settings_command")
    settings_sub.add_parser("open", help="Open settings")

    sub.add_parser("windows-smoke", help="Check optional Windows adapter imports")
    sub.add_parser("run-windows-app", help="Start the Windows hotkey dictation overlay")
    tray = sub.add_parser("run-windows-tray", help="Start the Windows tray controller")
    tray.add_argument("--no-autostart", action="store_true", help="Do not launch dictation immediately")
    return parser


def normalize_argv_for_packaged_app(argv: list[str], *, frozen: bool | None = None) -> list[str]:
    is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    if is_frozen and not argv:
        return ["run-windows-tray"]
    return list(argv)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    effective_argv = normalize_argv_for_packaged_app(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(effective_argv)
    config = load_config(args.config)

    if args.command in {"run-windows-app", "run-windows-tray"}:
        log_path = configure_file_logging()
        logging.getLogger("fastwispr.cli").info("starting command=%s config=%s log=%s", args.command, resolve_config_path(args.config), log_path)

    if args.command == "process":
        with Store(config.db_path) as store:
            print(process_text_with_store(" ".join(args.text), store).final)
        return 0

    if args.command == "init-db":
        init_db(config.db_path)
        print(config.db_path)
        return 0

    if args.command == "add-dictionary":
        with Store(config.db_path) as store:
            store.upsert_dictionary(args.term, args.replacement)
        return 0

    if args.command == "dictionary":
        with Store(config.db_path) as store:
            if args.dictionary_command == "list":
                for entry in store.dictionary_entries():
                    print(f"{entry.term} -> {entry.replacement}")
                return 0
            if args.dictionary_command == "add":
                store.upsert_dictionary(args.term, args.replacement)
                print(f"{args.term} -> {args.replacement}")
                return 0
            if args.dictionary_command == "remove":
                removed = store.delete_dictionary(args.term)
                print(f"removed {removed}")
                return 0
        parser.error("dictionary requires list, add, or remove")

    if args.command == "add-snippet":
        with Store(config.db_path) as store:
            store.upsert_snippet(args.cue, args.body)
        return 0

    if args.command == "transcribe":
        provider = args.provider or config.stt_provider
        model = args.model or config.stt_model
        language = args.language or config.stt_language
        device = args.device or config.stt_device
        compute_type = args.compute_type or config.stt_compute_type
        print(make_stt(provider, model, device, compute_type, language).transcribe(Path(args.audio_path)))
        return 0

    if args.command == "history":
        with Store(config.db_path) as store:
            events = store.recent_dictation_events(
                limit=args.limit,
                skipped_only=args.skipped_only,
                language=args.language,
            )
        if args.json:
            print(json.dumps([event.to_dict() for event in events], ensure_ascii=False, indent=2))
        else:
            print_history(events)
        return 0

    if args.command == "calibrate-audio":
        return calibrate_audio(config, resolve_config_path(args.config), args.seconds, apply=args.apply)

    if args.command == "config":
        path = resolve_config_path(args.config)
        if args.config_command == "show":
            print(config_to_toml(config))
            return 0
        if args.config_command == "set":
            set_config_value(path, args.key, args.value)
            print(f"{args.key} = {args.value}")
            return 0
        parser.error("config requires show or set")

    if args.command == "backup":
        path = resolve_config_path(args.config)
        with Store(config.db_path) as store:
            if args.backup_command == "export":
                write_backup(path, store, Path(args.path))
                print(args.path)
                return 0
            if args.backup_command == "import":
                counts = import_backup(path, store, Path(args.path))
                print(f"imported dictionary={counts['dictionary']} snippets={counts['snippets']}")
                return 0
        parser.error("backup requires export or import")

    if args.command == "settings":
        if args.settings_command == "open":
            from .windows.settings_ui import open_settings_window

            open_settings_window(resolve_config_path(args.config))
            return 0
        parser.error("settings requires open")

    if args.command == "windows-smoke":
        return windows_smoke()

    if args.command == "run-windows-app":
        run_windows_app(config)
        return 0

    if args.command == "run-windows-tray":
        from .windows.tray import run_tray

        run_tray(resolve_config_path(args.config), autostart=not args.no_autostart)
        return 0

    parser.print_help()
    return 2


def windows_smoke() -> int:
    checks = [
        ("hotkeys", "fastwispr.windows.hotkeys", "KeyboardHotkeyListener", lambda attr: attr("ctrl+space")),
        ("audio", "fastwispr.windows.audio", "SounddeviceRecorder", lambda attr: attr()),
        ("paste", "fastwispr.windows.injector", "ClipboardPasteInjector", lambda attr: attr()),
        ("tray", "fastwispr.windows.tray", "FastWisprTrayController", lambda attr: attr()),
        ("settings", "fastwispr.windows.settings_ui", "settings_values_from_config", lambda attr: attr),
    ]
    failed = False
    for name, module_name, attr_name, smoke in checks:
        try:
            module = __import__(module_name, fromlist=[attr_name])
            smoke(getattr(module, attr_name))
        except Exception as exc:
            failed = True
            print(f"{name}: unavailable ({exc})", file=sys.stderr)
        else:
            print(f"{name}: ok")
    return 1 if failed else 0


def print_history(events: list[DictationEvent]) -> None:
    for event in events:
        status = f"skipped:{event.skipped_reason}" if event.skipped_reason else "ok"
        audio = f"{event.audio_duration_ms or 0}ms"
        latency = f"{event.latency_ms or 0}ms"
        stt = f"{event.stt_latency_ms or 0}ms"
        language = event.language or "-"
        probability = "" if event.language_probability is None else f"({event.language_probability:.2f})"
        text = event.final_text.replace("\n", " ")
        print(f"#{event.id} {status} audio={audio} total={latency} stt={stt} lang={language}{probability} {text}")


def calibrate_audio(config: Config, config_path: Path, seconds: float, *, apply: bool = False) -> int:
    from .windows.audio import SounddeviceRecorder

    with TemporaryDirectory(prefix="fastwispr-calibrate-") as tmp:
        wav_path = Path(tmp) / "ambient.wav"
        SounddeviceRecorder().record_seconds(wav_path, seconds)
        stats = analyze_wav(wav_path)
    suggested = suggest_min_audio_rms(stats.rms_level)
    print(f"ambient_duration_ms={stats.duration_ms}")
    print(f"ambient_rms={stats.rms_level:.6f}")
    print(f"ambient_peak={stats.peak_level:.6f}")
    print(f"suggested_min_audio_rms={suggested:.6f}")
    if apply:
        set_config_value(config_path, "dictation.min_audio_rms", f"{suggested:g}")
        print(f"applied dictation.min_audio_rms={suggested:g}")
    else:
        print(f"apply with: python -m fastwispr.cli config set dictation.min_audio_rms {suggested:g}")
    return 0


def suggest_min_audio_rms(noise_rms: float) -> float:
    return round(max(0.003, min(0.03, noise_rms * 2.5)), 6)


def config_to_toml(config: Config) -> str:
    return "\n".join(
        [
            "[storage]",
            f"db_path = {quote_string(str(config.db_path))}",
            "",
            "[hotkeys]",
            f"dictate_toggle = {quote_string(config.hotkey)}",
            f"hold_button = {quote_string(config.hold_button)}",
            "",
            "[activation]",
            f"trigger = {quote_string(config.activation_trigger)}",
            f"mode = {quote_string(config.activation_mode)}",
            "",
            "[stt]",
            f"provider = {quote_string(config.stt_provider)}",
            f"model = {quote_string(config.stt_model)}",
            f"language = {quote_string(config.stt_language)}",
            f"device = {quote_string(config.stt_device)}",
            f"compute_type = {quote_string(config.stt_compute_type)}",
            "",
            "[dictation]",
            f"min_record_seconds = {config.min_record_seconds:g}",
            f"min_audio_rms = {config.min_audio_rms:g}",
            "",
            "[privacy]",
            f"store_audio = {bool_to_toml(config.store_audio)}",
            f"store_raw_transcripts = {bool_to_toml(config.store_raw_transcripts)}",
            "",
            "[injection]",
            f"restore_clipboard = {bool_to_toml(config.restore_clipboard)}",
        ]
    )


def set_config_value(path: Path, key: str, raw_value: str) -> None:
    data = read_config_dict(path)
    section, option = split_config_key(key)
    value = parse_config_value(section, option, raw_value)
    data.setdefault(section, {})[option] = value
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
    supported: dict[str, set[str]] = {
        "storage": {"db_path"},
        "hotkeys": {"dictate_toggle", "hold_button"},
        "activation": {"trigger", "mode"},
        "stt": {"provider", "model", "language", "device", "compute_type"},
        "dictation": {"min_record_seconds", "min_audio_rms"},
        "privacy": {"store_audio", "store_raw_transcripts"},
        "injection": {"restore_clipboard"},
    }
    if option not in supported.get(section, set()):
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
    sections = ["storage", "hotkeys", "activation", "stt", "dictation", "privacy", "injection"]
    lines: list[str] = []
    for section in sections + sorted(set(data) - set(sections)):
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
        return bool_to_toml(value)
    if isinstance(value, int | float):
        return f"{value:g}"
    return quote_string(str(value))


def bool_to_toml(value: bool) -> str:
    return "true" if value else "false"


def quote_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


if __name__ == "__main__":
    raise SystemExit(main())
