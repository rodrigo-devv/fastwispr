# MVP UI Build Brief

## Goal

Build a Windows-native local-first hold-to-talk dictation MVP for long technical prompts and chat instructions.

## Decided

- Input is hold-to-talk on Mouse 4.
- Mouse 4 maps to Win32 `XBUTTON1` by default, with config fallback to `xbutton2`.
- The overlay is visual-only and should not steal focus.
- The focused target app remains the paste destination.
- The UI is a floating audio bar, roughly 50px tall and 200–300px wide.
- Silence renders as `.....`.
- Detected speech renders as a waveform driven by real microphone RMS level.
- STT is local `faster-whisper` using model `small`, device `cpu`, compute type `int8` first.
- Language detection is automatic; MVP supports English and Portuguese via Whisper language detection.
- Long dictation is safe: record while held, transcribe after release, paste one final block.
- Default polish is conservative: punctuation/capitalization, filler cleanup, dictionary/snippets; no LLM rewrite, no summary.
- Backlog: free-record/toggle mode where one press starts and another press stops.

## Non-goals

- Streaming partial paste.
- Aggressive rewriting or LLM cleanup.
- Config UI for hotkeys.
- SaaS/account/sync behavior.
- Polished tray app packaging.

## Architecture

- `windows.mouse_buttons`: low-level Win32 mouse hook for `XBUTTON1/XBUTTON2`.
- `windows.audio`: raw `sounddevice.RawInputStream` recorder, no NumPy requirement for capture path.
- `windows.overlay`: Tk floating overlay with silence dots and waveform bars.
- `windows.hold_to_talk`: orchestration glue for mouse press/release, recording, transcribing, and paste.
- `stt`: `faster-whisper` adapter with text + language metadata.
- `controller`: reusable finish-from-audio path for UI-recorded WAV files.

## Failure modes and handling

- Wrong mouse side button: switch `[hotkeys].hold_button` from `xbutton1` to `xbutton2`.
- No speech/audio device issue: overlay remains silent or STT returns empty; record-smoke validates mic bytes first.
- STT unavailable: command fails with explicit install hint for `.[stt]`.
- Paste target wrong: overlay is no-activate/click-through; mouse hook swallows side-button events to avoid browser back.
- Long prompt: audio is buffered to a temporary WAV and removed after processing.

## Acceptance criteria

- Unit tests pass on Linux/WSL.
- Unit tests pass on Windows.
- Windows smoke imports audio/paste/hotkey adapters.
- `record-smoke` records bytes through the interactive runner.
- Holding Mouse 4 shows overlay and waveform when speaking.
- Releasing Mouse 4 transcribes and pastes one final block into the previously focused editor.
- No raw audio persists after dictation by default.
