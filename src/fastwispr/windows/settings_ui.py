from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ..config import Config
from ..config_edit import set_config_value

SETTINGS_FIELDS = [
    ("hotkeys.dictate_toggle", "Keyboard hotkey"),
    ("hotkeys.hold_button", "Mouse hold button"),
    ("activation.trigger", "Trigger: keyboard or mouse"),
    ("activation.mode", "Mode: toggle or hold"),
    ("stt.language", "Language"),
    ("stt.model", "STT model"),
    ("stt.device", "STT device"),
    ("stt.compute_type", "STT compute type"),
    ("dictation.min_record_seconds", "Minimum record seconds"),
    ("dictation.min_audio_rms", "Minimum audio RMS"),
    ("injection.restore_clipboard", "Restore clipboard"),
]


def settings_values_from_config(config: Config) -> dict[str, str]:
    return {
        "hotkeys.dictate_toggle": config.hotkey,
        "hotkeys.hold_button": config.hold_button,
        "activation.trigger": config.activation_trigger,
        "activation.mode": config.activation_mode,
        "stt.language": config.stt_language,
        "stt.model": config.stt_model,
        "stt.device": config.stt_device,
        "stt.compute_type": config.stt_compute_type,
        "dictation.min_record_seconds": f"{config.min_record_seconds:g}",
        "dictation.min_audio_rms": f"{config.min_audio_rms:g}",
        "injection.restore_clipboard": "true" if config.restore_clipboard else "false",
    }


def save_settings_values(config_path: Path, values: Mapping[str, str]) -> None:
    allowed = {key for key, _label in SETTINGS_FIELDS}
    for key, value in values.items():
        if key not in allowed:
            raise ValueError(f"Unsupported settings key: {key}")
        set_config_value(config_path, key, value)


def open_settings_window(config_path: Path) -> None:  # pragma: no cover - GUI smoke is manual/Windows
    import tkinter as tk
    from tkinter import messagebox

    from ..config import load_config

    root = tk.Tk()
    root.title("FastWispr Settings")
    root.resizable(False, False)
    values = settings_values_from_config(load_config(config_path))
    variables: dict[str, tk.StringVar] = {}

    for row, (key, label) in enumerate(SETTINGS_FIELDS):
        tk.Label(root, text=label, anchor="w").grid(row=row, column=0, sticky="w", padx=12, pady=4)
        variable = tk.StringVar(value=values[key])
        variables[key] = variable
        tk.Entry(root, textvariable=variable, width=32).grid(row=row, column=1, sticky="ew", padx=12, pady=4)

    def save() -> None:
        try:
            save_settings_values(config_path, {key: variable.get().strip() for key, variable in variables.items()})
        except Exception as exc:
            messagebox.showerror("FastWispr Settings", str(exc))
            return
        messagebox.showinfo("FastWispr Settings", "Settings saved. Restart dictation to apply changes.")
        root.destroy()

    button_row = len(SETTINGS_FIELDS)
    tk.Button(root, text="Save", command=save).grid(row=button_row, column=0, padx=12, pady=12, sticky="ew")
    tk.Button(root, text="Cancel", command=root.destroy).grid(row=button_row, column=1, padx=12, pady=12, sticky="ew")
    root.mainloop()
