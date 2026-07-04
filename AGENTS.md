# FastWispr — Agent Rules

Target product: Windows-native local-first voice dictation tool for Rodrigo.

## Scope

Build MVP first:

1. Windows global hotkey starts/stops dictation.
2. Microphone audio capture.
3. Local STT adapter.
4. Transcript cleanup/polish.
5. Dictionary + snippets.
6. Clipboard-safe paste into focused app.

This repo may be edited from Linux/WSL, but runtime target is Windows. Keep OS-specific code isolated so pure logic remains testable in Linux.

## Ponytail mode

Act like a lazy senior developer. Before coding, inspect the touched flow and choose the first rung that works: avoid building if YAGNI; reuse existing code; use stdlib; use native platform features; use installed deps; one-line/local diff; only then write minimum new code. No speculative abstractions, no new dependency unless necessary, deletion over addition, fewest files possible. Fix root cause, not symptom. Keep validation/security/accessibility/data-loss handling. Add only the smallest runnable check for non-trivial logic. Report files changed and exact verification commands/results.

## Implementation rules

- Keep source, docs, prompts, UI, filenames, and public-facing text product-original.
- Do not use third-party code, branding, assets, UI, marketing language, private APIs, or endpoint behavior.
- Default privacy: no audio storage; no cloud calls by default.
- Use Python 3.11+ unless there is a strong reason not to.
- Prefer SQLite + stdlib where possible.
- Optional heavy deps (`faster-whisper`, Windows input libs) should be install extras or documented, not imported at package import time if tests can avoid them.
- Tests must run in this Linux/WSL environment for pure logic.
- Windows smoke steps must be documented if they cannot be executed here.

## Verification expectation

At minimum, run:

```bash
python -m pytest
```

If pytest is unavailable, create/use a venv and install package test deps. No fake test output. If Windows desktop integration cannot be smoke-tested in this environment, say so directly and provide exact PowerShell commands for Rodrigo to run on Windows.
