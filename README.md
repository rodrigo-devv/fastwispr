# FastWispr

FastWispr is a local-first dictation app for Windows. Press a hotkey, speak naturally, and the text is transcribed locally, lightly cleaned up, and pasted into whatever app is focused.

It is built for people who write all day and do not want voice input to become another cloud account, browser extension, or productivity ritual. The goal is simple: talk, get usable text, keep working.

## Why FastWispr exists

Most voice tools are either too heavy, too cloud-dependent, or too tied to one editor. FastWispr is intentionally boring in the good way:

- **Local by default** — speech-to-text runs on your machine with `faster-whisper`.
- **Private by default** — no cloud calls, no audio storage, no raw transcript storage unless explicitly configured.
- **Works across apps** — the final text is pasted into the currently focused Windows app.
- **Fast to trigger** — default `Ctrl+Space` starts recording and `Ctrl+Space` stops, transcribes, and pastes.
- **Does not steal your keys** — the global hotkey is pass-through, so Windows, games, and normal apps still receive Ctrl/Space.
- **User vocabulary friendly** — local dictionary and snippets help with project names, tools, acronyms, and repeated text.
- **Hackable core** — most of the logic is pure Python and testable from Linux/WSL; Windows-specific pieces are isolated behind adapters.

## Current status

FastWispr is an early personal productivity build, but the core loop is already working:

1. Listen for a global hotkey.
2. Record microphone audio.
3. Transcribe locally with Whisper-family STT.
4. Clean obvious filler/correction phrases.
5. Apply dictionary replacements and snippets.
6. Paste the final text into the active Windows app.
7. Log local dictation metrics to SQLite for debugging.

It has been manually dogfooded on Windows with normal apps and Path of Exile 2. The hotkey remains usable by the game because FastWispr observes keyboard events instead of suppressing them.

## Tech stack

- **Python 3.11+** for the app core and Windows adapters.
- **faster-whisper** for local speech-to-text.
- **SQLite** for dictionary entries, snippets, settings, and optional dictation event history.
- **keyboard** for global keyboard hotkeys on Windows.
- **sounddevice** for microphone recording.
- **pyperclip + pyautogui** for clipboard-based paste injection.
- **pystray** for the Windows tray controller.
- **tkinter** from the Python standard library for the first settings window.
- **PyInstaller** for the first Windows one-folder build.
- **pytest** for the cross-platform test suite.
- **PowerShell scripts** for Windows startup and local runner workflows.

No STT or Windows desktop dependency is imported at package import time unless that feature is actually used.

## Quick start on Windows

Run this from normal Windows PowerShell in the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\setup.ps1
```

Start the tray app:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start-ui.ps1
```

Default controls:

```text
Ctrl+Space  start recording
Ctrl+Space  stop, transcribe, paste
```

Mouse 4 hold-to-talk is still available as a fallback:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start-ui.ps1 -Trigger mouse -ActivationMode hold -HoldButton xbutton1
```

## Development from Linux/WSL

The pure Python core can be developed and tested from Linux/WSL:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
python -m pytest
python -m fastwispr.cli process "um meet at five actually six and tail scale"
```

Example output:

```text
Meet at six and tail scale.
```

The Windows desktop pieces still need Windows for real microphone, hotkey, and focused-app paste validation.

## Configuration

FastWispr writes config under `%APPDATA%\FastWispr\config.toml` on Windows unless `--config` is provided.

Inspect config:

```powershell
python -m fastwispr.cli config show
```

Common settings:

```powershell
python -m fastwispr.cli config set hotkeys.dictate_toggle ctrl+space
python -m fastwispr.cli config set activation.trigger keyboard
python -m fastwispr.cli config set activation.mode toggle
python -m fastwispr.cli config set stt.language pt-en
python -m fastwispr.cli config set dictation.min_record_seconds 0.35
python -m fastwispr.cli config set dictation.min_audio_rms 0.003
```

Language modes:

```powershell
# bilingual Portuguese/English default
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start-ui.ps1 -Language pt-en

# force one language when testing
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start-ui.ps1 -Language pt-BR
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start-ui.ps1 -Language en
```

## Dictionary and snippets

Dictionary entries fix recurring recognition mistakes:

```powershell
python -m fastwispr.cli dictionary add "tail scale" "Tailscale"
python -m fastwispr.cli dictionary list
python -m fastwispr.cli dictionary remove "tail scale"
```

Snippets expand a spoken cue into fixed text:

```powershell
python -m fastwispr.cli add-snippet "insert scheduling link" "https://cal.com/rodrigo"
```

## Audio guards

FastWispr avoids sending obvious bad captures to STT:

- `min_record_seconds` skips accidental taps.
- `min_audio_rms` skips silence.
- invalid/corrupt WAVs are logged as `invalid_audio`.

Calibrate ambient noise:

```powershell
python -m fastwispr.cli calibrate-audio --seconds 5
python -m fastwispr.cli calibrate-audio --seconds 5 --apply
```

## Local history

Dictation events can be inspected locally:

```powershell
python -m fastwispr.cli history --limit 10
python -m fastwispr.cli history --limit 20 --json
python -m fastwispr.cli history --skipped-only
```

Recorded metrics include audio duration, RMS/peak, STT latency, total latency, detected language, language probability, final text, and skipped reason. Raw transcript and audio storage are off by default.

## Windows startup

Install startup shortcut:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\install-startup-shortcut.ps1
```

Remove startup shortcut:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\uninstall-startup-shortcut.ps1
```

`start-ui.ps1` intentionally does not install dependencies during login/startup. Install or update dependencies with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\setup.ps1
```

so startup stays fast and offline-safe.

## Tray and settings

The tray controller starts FastWispr as a child process and keeps the dictation engine separate from tray UI code. Menu actions:

```text
Start FastWispr
Stop FastWispr
Settings
Quit
```

Open settings directly:

```powershell
python -m fastwispr.cli settings open
```

The first settings UI is intentionally simple and uses stdlib `tkinter`; no Electron/Qt tax for a handful of fields.

## Backup export/import

Export config, dictionary, and snippets to JSON:

```powershell
python -m fastwispr.cli backup export .\fastwispr-backup.json
```

Import into the current config/database:

```powershell
python -m fastwispr.cli backup import .\fastwispr-backup.json
```

Backups intentionally exclude dictation history, raw transcripts, and audio.

## Windows build

Build the first one-folder executable with PyInstaller:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\build.ps1
```

Output:

```text
dist\FastWispr\FastWispr.exe
```

## Verification

Current baseline:

```bash
python -m pytest -q
```

Expected on the current version:

```text
76 passed
```

Windows smoke:

```powershell
python -m fastwispr.cli windows-smoke
```

Expected modules:

```text
hotkeys: ok
audio: ok
paste: ok
tray: ok
settings: ok
```

## Roadmap

Near-term:

- Make tray startup fully silent/no-console for daily use.
- Add a proper installer/update path around the one-folder build.
- Improve the overlay polish while keeping it small and non-distracting.
- Add configurable STT parameters for speed/accuracy trade-offs.
- Add optional encrypted sync for dictionary/snippets/settings.

Later:

- Optional encrypted sync for dictionaries/snippets/settings.
- Optional cloud fallback for machines without local STT capacity.
- A more native Windows shell if Python UI limits become annoying.

## License

Private/internal for now unless a license file is added later.
