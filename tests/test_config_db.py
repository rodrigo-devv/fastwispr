from pathlib import Path
import pytest

from fastwispr.config import load_config
from fastwispr.db import Store


def test_config_reads_toml(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "custom.sqlite3"
    db_path_toml = db_path.as_posix()
    config_path.write_text(
        f"""
[storage]
db_path = "{db_path_toml}"

[hotkeys]
dictate_toggle = "ctrl+alt+space"
hold_button = "xbutton2"

[activation]
mode = "toggle"

[stt]
provider = "faster-whisper"
model = "small"
language = "pt-BR"

[dictation]
min_record_seconds = 0.45
min_audio_rms = 0.004

[privacy]
store_audio = true
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.db_path == db_path
    assert config.hotkey == "ctrl+alt+space"
    assert config.hold_button == "xbutton2"
    assert config.activation_mode == "toggle"
    assert config.stt_provider == "faster-whisper"
    assert config.stt_model == "small"
    assert config.stt_language == "pt-BR"
    assert config.min_record_seconds == 0.45
    assert config.min_audio_rms == 0.004
    assert config.store_audio is True
    assert config.store_raw_transcripts is False


def test_config_reads_powershell_utf8_bom_toml(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[hotkeys]
hold_button = "xbutton1"

[stt]
provider = "faster-whisper"
model = "small"
""".lstrip(),
        encoding="utf-8-sig",
    )

    config = load_config(config_path)

    assert config.hotkey == "ctrl+space"
    assert config.activation_trigger == "keyboard"
    assert config.hold_button == "xbutton1"
    assert config.activation_mode == "toggle"
    assert config.stt_provider == "faster-whisper"
    assert config.stt_model == "small"
    assert config.stt_language == "pt-en"
    assert config.min_record_seconds == 0.35
    assert config.min_audio_rms == 0.003


def test_config_reads_activation_trigger(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[activation]
trigger = "mouse"
mode = "hold"
""".lstrip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.activation_trigger == "mouse"
    assert config.activation_mode == "hold"


def test_config_reads_boolean_strings_without_truthy_false_bug(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[privacy]
store_audio = "false"
store_raw_transcripts = "false"

[injection]
restore_clipboard = "false"
""".lstrip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.store_audio is False
    assert config.store_raw_transcripts is False
    assert config.restore_clipboard is False


def test_config_rejects_invalid_boolean_string(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[privacy]
store_audio = "maybe"
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="privacy.store_audio"):
        load_config(config_path)


def test_store_dictionary_snippets_settings_and_dictation_history(tmp_path: Path):
    with Store(tmp_path / "fastwispr.sqlite3") as store:
        store.upsert_dictionary("tail scale", "Tailscale")
        store.upsert_snippet("insert scheduling link", "https://cal.com/rodrigo")
        store.set_setting("hotkey", "ctrl+space")
        store.record_dictation_event(
            raw_transcript=None,
            final_text="Hello project.",
            latency_ms=123,
            stt_latency_ms=100,
            audio_duration_ms=900,
            language="en",
            language_probability=0.94,
            audio_rms=0.05,
            audio_peak=0.12,
            skipped_reason=None,
        )

        assert store.dictionary_entries()[0].replacement == "Tailscale"
        assert store.snippets()[0].body == "https://cal.com/rodrigo"
        assert store.get_setting("hotkey") == "ctrl+space"
        event = store.recent_dictation_events(limit=1)[0]
        assert event.final_text == "Hello project."
        assert event.latency_ms == 123
        assert event.stt_latency_ms == 100
        assert event.audio_duration_ms == 900
        assert event.language == "en"
        assert event.language_probability == 0.94
        assert event.audio_rms == 0.05
        assert event.audio_peak == 0.12
        assert event.skipped_reason is None


def test_process_command_accepts_unquoted_words(tmp_path: Path, capsys):
    from fastwispr.cli import main

    config_path = tmp_path / "config.toml"
    db_path = (tmp_path / "fastwispr.sqlite3").as_posix()
    config_path.write_text(
        f"""
[storage]
db_path = "{db_path}"
""",
        encoding="utf-8",
    )

    assert main(["--config", str(config_path), "process", "um", "meet", "at", "five", "actually", "six"]) == 0

    assert capsys.readouterr().out.strip() == "Meet at six."


def test_config_cli_show_and_set(tmp_path: Path, capsys):
    from fastwispr.cli import main

    config_path = tmp_path / "config.toml"

    assert main(["--config", str(config_path), "config", "set", "stt.language", "en"]) == 0
    assert main(["--config", str(config_path), "config", "set", "dictation.min_record_seconds", "0.5"]) == 0
    assert main(["--config", str(config_path), "config", "set", "activation.mode", "toggle"]) == 0

    config = load_config(config_path)
    assert config.stt_language == "en"
    assert config.min_record_seconds == 0.5
    assert config.activation_mode == "toggle"

    assert main(["--config", str(config_path), "config", "show"]) == 0
    output = capsys.readouterr().out
    assert 'language = "en"' in output
    assert "min_record_seconds = 0.5" in output
    assert 'mode = "toggle"' in output


def test_config_cli_rejects_unknown_keys(tmp_path: Path):
    from fastwispr.cli import main

    with pytest.raises(SystemExit, match="Unsupported config key"):
        main(["--config", str(tmp_path / "config.toml"), "config", "set", "hotkeys.typo", "x"])


def test_store_rejects_empty_dictionary_and_snippet_keys(tmp_path: Path):
    with Store(tmp_path / "fastwispr.sqlite3") as store:
        with pytest.raises(ValueError, match="Dictionary term"):
            store.upsert_dictionary("   ", "Rust")
        with pytest.raises(ValueError, match="Snippet cue"):
            store.upsert_snippet("   ", "body")


def test_history_command_prints_recent_dictation_metrics(tmp_path: Path, capsys):
    from fastwispr.cli import main

    config_path = tmp_path / "config.toml"
    db_path = (tmp_path / "fastwispr.sqlite3").as_posix()
    config_path.write_text(f"[storage]\ndb_path = \"{db_path}\"\n", encoding="utf-8")
    with Store(db_path) as store:
        store.record_dictation_event(
            raw_transcript=None,
            final_text="Hello project.",
            latency_ms=123,
            stt_latency_ms=100,
            audio_duration_ms=900,
            language="en",
            language_probability=0.94,
            audio_rms=0.05,
            audio_peak=0.12,
            skipped_reason=None,
        )

    assert main(["--config", str(config_path), "history", "--limit", "1"]) == 0

    output = capsys.readouterr().out
    assert "ok" in output
    assert "900ms" in output
    assert "123ms" in output
    assert "en" in output
    assert "Hello project." in output


def test_history_command_supports_json_filters(tmp_path: Path, capsys):
    import json
    from fastwispr.cli import main

    config_path = tmp_path / "config.toml"
    db_path = (tmp_path / "fastwispr.sqlite3").as_posix()
    config_path.write_text(f"[storage]\ndb_path = \"{db_path}\"\n", encoding="utf-8")
    with Store(db_path) as store:
        store.record_dictation_event(
            raw_transcript=None,
            final_text="Hello project.",
            latency_ms=123,
            stt_latency_ms=100,
            audio_duration_ms=900,
            language="en",
            language_probability=0.94,
            audio_rms=0.05,
            audio_peak=0.12,
            skipped_reason=None,
        )
        store.record_dictation_event(
            raw_transcript=None,
            final_text="",
            latency_ms=10,
            stt_latency_ms=None,
            audio_duration_ms=100,
            language=None,
            language_probability=None,
            audio_rms=0.0,
            audio_peak=0.0,
            skipped_reason="silence",
        )

    assert main(["--config", str(config_path), "history", "--limit", "10", "--json", "--language", "en"]) == 0
    events = json.loads(capsys.readouterr().out)
    assert len(events) == 1
    assert events[0]["language"] == "en"
    assert events[0]["final_text"] == "Hello project."

    assert main(["--config", str(config_path), "history", "--skipped-only"]) == 0
    output = capsys.readouterr().out
    assert "skipped:silence" in output
    assert "Hello project." not in output


def test_dictionary_cli_list_add_remove(tmp_path: Path, capsys):
    from fastwispr.cli import main

    config_path = tmp_path / "config.toml"
    db_path = (tmp_path / "fastwispr.sqlite3").as_posix()
    config_path.write_text(f"[storage]\ndb_path = \"{db_path}\"\n", encoding="utf-8")

    assert main(["--config", str(config_path), "dictionary", "add", "runt", "Rust"]) == 0
    assert main(["--config", str(config_path), "dictionary", "list"]) == 0
    assert "runt -> Rust" in capsys.readouterr().out

    assert main(["--config", str(config_path), "dictionary", "remove", "runt"]) == 0
    assert main(["--config", str(config_path), "dictionary", "list"]) == 0
    assert "runt -> Rust" not in capsys.readouterr().out


def test_calibration_suggests_threshold_from_noise_floor():
    from fastwispr.cli import suggest_min_audio_rms

    assert suggest_min_audio_rms(0.001) == 0.003
    assert suggest_min_audio_rms(0.004) == 0.01
