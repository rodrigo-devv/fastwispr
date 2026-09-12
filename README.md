# FastWispr

**Open-source, local-first voice dictation for Windows.**

Press a hotkey, speak, release — the text is transcribed **on your machine** and pasted into whatever app is focused.

A privacy-first alternative to [Wispr Flow](https://wisprflow.ai) and similar cloud dictation tools (Superwhisper, Typeless, etc.): **no account, no subscription, no audio upload.**

> Not affiliated with Wispr Flow / wisprflow.ai. FastWispr is an independent open-source project.

[![tests](https://github.com/rodrigo-devv/fastwispr/actions/workflows/test.yml/badge.svg)](https://github.com/rodrigo-devv/fastwispr/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Why this exists

Cloud dictation is polished, but it sends everything you say to someone else's servers and charges a monthly fee.

FastWispr is the boring, inspectable version:

| | FastWispr | Typical cloud dictation (Wispr Flow & similar) |
|---|---|---|
| Source | Open (MIT) | Closed |
| Speech-to-text | On-device (`faster-whisper`) | Cloud |
| Audio leaves the machine | No (STT is local) | Yes |
| Account / subscription | No | Yes |
| Platform | Windows | Often Mac-first + Windows |
| LLM rewrite / “Flow mode” | Not yet (rule-based cleanup only) | Yes |
| Works in any focused app | Yes (clipboard paste) | Yes |

**Honest limits:** Windows only. No macOS/Linux desktop app. No cloud LLM polish. First run may download a Whisper model from Hugging Face if it is not already cached.

## How it works

```text
Ctrl+Space  →  record
Ctrl+Space  →  stop → local Whisper STT → light cleanup → paste into focused app
```

1. Global hotkey (pass-through — does not steal Ctrl/Space from games or Windows).
2. Record microphone audio.
3. Transcribe locally with `faster-whisper`.
4. Strip fillers / simple corrections, apply dictionary + snippets.
5. Paste into the currently focused Windows app.
6. Optional local SQLite history for debugging. Raw audio and raw transcripts are **off** by default.

Default language mode is bilingual `pt-en` (Portuguese + English, transcribe, do not translate).

## Quick start (Windows)

From PowerShell in the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\setup.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start-ui.ps1
```

Default: `Ctrl+Space` toggle. Mouse 4 hold-to-talk is a fallback:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start-ui.ps1 -Trigger mouse -ActivationMode hold -HoldButton xbutton1
```

Packaged build (one-folder exe):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\build.ps1
# dist\FastWispr\FastWispr.exe        tray app
# dist\FastWisprCli\FastWisprCli.exe  diagnostics
```

## Develop / test from Linux or WSL

The Python core is testable without Windows:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
python -m pytest -q
python -m fastwispr.cli process "um meet at five actually six and tail scale"
# Meet at six and tail scale.
```

Microphone, global hotkey, overlay, and paste still need a real Windows desktop session.

## Stack

Python 3.11+ · faster-whisper · SQLite · `keyboard` / `sounddevice` / `pyperclip` / `pyautogui` / `pystray` · stdlib `tkinter` settings · PyInstaller · pytest

Heavy STT and Windows deps are **optional extras**, not imported at package import time.

## Config, dictionary, snippets

Config lives in `%APPDATA%\FastWispr\config.toml` unless `--config` is set.

```powershell
python -m fastwispr.cli config show
python -m fastwispr.cli config set hotkeys.dictate_toggle ctrl+space
python -m fastwispr.cli config set stt.language pt-en
python -m fastwispr.cli dictionary add "tail scale" "Tailscale"
python -m fastwispr.cli add-snippet "insert meeting link" "https://example.com/meet"
python -m fastwispr.cli backup export .\fastwispr-backup.json
```

Language smoke:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start-ui.ps1 -Language pt-en
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start-ui.ps1 -Language pt-BR
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start-ui.ps1 -Language en
```

## Audio guards

- `min_record_seconds` skips accidental taps
- `min_audio_rms` skips silence
- invalid WAVs are logged as `invalid_audio` before STT

```powershell
python -m fastwispr.cli calibrate-audio --seconds 5 --apply
```

## Tray, logs, presets

Tray: Start / Stop / Settings / Open Logs / Quit. Engine runs as a child process.

Log file: `%APPDATA%\FastWispr\fastwispr.log`

| Preset | Model | Device | Compute |
|---|---|---|---|
| Fast | `base` | CPU | int8 |
| Balanced | `small` | CPU | int8 |
| Accurate | `medium` | CPU | int8 |

Single-instance via Windows mutex — a second launch shows a warning instead of duplicating hotkeys.

## Verification

```bash
python -m pytest -q    # 95 passed on current main
```

Windows:

```powershell
python -m fastwispr.cli windows-smoke
python -m fastwispr.cli sound-smoke
```

Expected: `hotkeys`, `audio`, `paste`, `tray`, `settings`, `single-instance`, `sound` all `ok`.

## Roadmap

- Overlay / settings polish without adding a UI framework
- Optional encrypted sync for dictionary / snippets / config
- Optional LLM rewrite **local-only** (e.g. Ollama) — not a cloud default
- Installer only if distribution outgrows the one-folder exe

## License

[MIT](LICENSE) — use it, fork it, audit it.

Repo: [github.com/rodrigo-devv/fastwispr](https://github.com/rodrigo-devv/fastwispr)
