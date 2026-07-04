from pathlib import Path

from fastwispr.config import load_config
from fastwispr.windows.settings_ui import settings_values_from_config, save_settings_values


def test_settings_values_from_config_are_ui_strings(tmp_path: Path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[hotkeys]
dictate_toggle = "ctrl+alt+space"

[stt]
language = "en"

[dictation]
min_audio_rms = 0.004

[injection]
restore_clipboard = false
""".lstrip(),
        encoding="utf-8",
    )

    values = settings_values_from_config(load_config(config_path))

    assert values["hotkeys.dictate_toggle"] == "ctrl+alt+space"
    assert values["stt.language"] == "en"
    assert values["dictation.min_audio_rms"] == "0.004"
    assert values["injection.restore_clipboard"] == "false"


def test_save_settings_values_reuses_config_writer(tmp_path: Path):
    config_path = tmp_path / "config.toml"

    save_settings_values(
        config_path,
        {
            "hotkeys.dictate_toggle": "ctrl+space",
            "activation.trigger": "keyboard",
            "activation.mode": "toggle",
            "stt.language": "pt-en",
            "dictation.min_record_seconds": "0.35",
            "dictation.min_audio_rms": "0.003",
            "injection.restore_clipboard": "true",
        },
    )

    config = load_config(config_path)
    assert config.hotkey == "ctrl+space"
    assert config.activation_trigger == "keyboard"
    assert config.activation_mode == "toggle"
    assert config.stt_language == "pt-en"
    assert config.min_record_seconds == 0.35
    assert config.min_audio_rms == 0.003
    assert config.restore_clipboard is True
