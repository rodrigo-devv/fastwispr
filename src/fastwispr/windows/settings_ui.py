from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ..config import Config
from ..config_edit import set_config_value

STT_PRESET_FIELD = "stt.preset"
CUSTOM_PRESET = "Custom"
STT_PRESETS: dict[str, dict[str, str]] = {
    "Fast": {"stt.model": "base", "stt.device": "cpu", "stt.compute_type": "int8"},
    "Balanced": {"stt.model": "small", "stt.device": "cpu", "stt.compute_type": "int8"},
    "Accurate": {"stt.model": "medium", "stt.device": "cpu", "stt.compute_type": "int8"},
}
STT_PRESET_OPTIONS = [CUSTOM_PRESET, *STT_PRESETS.keys()]

SETTINGS_FIELDS = [
    ("hotkeys.dictate_toggle", "Keyboard hotkey"),
    ("hotkeys.hold_button", "Mouse hold button"),
    ("activation.trigger", "Trigger: keyboard or mouse"),
    ("activation.mode", "Mode: toggle or hold"),
    ("stt.language", "Language"),
    (STT_PRESET_FIELD, "STT preset"),
    ("stt.model", "STT model"),
    ("stt.device", "STT device"),
    ("stt.compute_type", "STT compute type"),
    ("dictation.min_record_seconds", "Minimum record seconds"),
    ("dictation.min_audio_rms", "Minimum audio RMS"),
    ("injection.restore_clipboard", "Restore clipboard"),
]
CONFIG_SETTING_KEYS = {key for key, _label in SETTINGS_FIELDS if key != STT_PRESET_FIELD}


def settings_values_from_config(config: Config) -> dict[str, str]:
    values = {
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
    values[STT_PRESET_FIELD] = stt_preset_from_values(values)
    return values


def stt_preset_from_values(values: Mapping[str, str]) -> str:
    for preset_name, preset_values in STT_PRESETS.items():
        if all(values.get(key) == value for key, value in preset_values.items()):
            return preset_name
    return CUSTOM_PRESET


def apply_stt_preset_to_values(values: Mapping[str, str], preset_name: str) -> dict[str, str]:
    updated = dict(values)
    if preset_name not in STT_PRESET_OPTIONS:
        raise ValueError(f"Unsupported STT preset: {preset_name}")
    updated[STT_PRESET_FIELD] = preset_name
    if preset_name != CUSTOM_PRESET:
        updated.update(STT_PRESETS[preset_name])
    return updated


def save_settings_values(config_path: Path, values: Mapping[str, str]) -> None:
    allowed = {key for key, _label in SETTINGS_FIELDS}
    unknown = set(values) - allowed
    if unknown:
        raise ValueError(f"Unsupported settings key: {sorted(unknown)[0]}")

    prepared = dict(values)
    preset_name = prepared.get(STT_PRESET_FIELD, CUSTOM_PRESET)
    if preset_name != CUSTOM_PRESET:
        prepared = apply_stt_preset_to_values(prepared, preset_name)

    for key, value in prepared.items():
        if key == STT_PRESET_FIELD:
            continue
        if key not in CONFIG_SETTING_KEYS:
            raise ValueError(f"Unsupported settings key: {key}")
        set_config_value(config_path, key, value)


def open_settings_window(config_path: Path) -> None:  # pragma: no cover - GUI smoke is manual/Windows
    import tkinter as tk
    from tkinter import messagebox, ttk

    from ..config import load_config

    root = tk.Tk()
    root.title("FastWispr Settings")
    root.resizable(False, False)
    values = settings_values_from_config(load_config(config_path))
    variables: dict[str, tk.StringVar] = {}

    def apply_preset_to_form(_event: object | None = None) -> None:
        preset_name = variables[STT_PRESET_FIELD].get().strip()
        try:
            updated = apply_stt_preset_to_values({key: variable.get().strip() for key, variable in variables.items()}, preset_name)
        except Exception as exc:
            messagebox.showerror("FastWispr Settings", str(exc))
            variables[STT_PRESET_FIELD].set(CUSTOM_PRESET)
            return
        for key in ("stt.model", "stt.device", "stt.compute_type"):
            variables[key].set(updated[key])

    for row, (key, label) in enumerate(SETTINGS_FIELDS):
        tk.Label(root, text=label, anchor="w").grid(row=row, column=0, sticky="w", padx=12, pady=4)
        variable = tk.StringVar(value=values[key])
        variables[key] = variable
        if key == STT_PRESET_FIELD:
            widget = ttk.Combobox(root, textvariable=variable, values=STT_PRESET_OPTIONS, state="readonly", width=29)
            widget.bind("<<ComboboxSelected>>", apply_preset_to_form)
        else:
            widget = tk.Entry(root, textvariable=variable, width=32)
        widget.grid(row=row, column=1, sticky="ew", padx=12, pady=4)

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
