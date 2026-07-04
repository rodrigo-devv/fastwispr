# FastWispr — Product Brief

## Product intent

Build a private, local-first voice input layer for Windows: the user speaks naturally, the app produces polished text, and the result is inserted into the currently focused application.

This is an original internal tool for personal productivity and future product exploration. Keep all implementation, naming, docs, and UI product-original.

## MVP outcome

The MVP should make this loop work reliably:

1. User presses a global hotkey.
2. App records microphone audio until the user stops.
3. STT converts speech to raw transcript.
4. Processor cleans the transcript into intended text.
5. Local dictionary/snippet rules apply user preferences.
6. App inserts the final text into the focused Windows app.
7. If insertion fails, final text remains available on the clipboard.

## Product principles

- Local-first by default.
- Private by default: no audio storage and no cloud calls unless explicitly enabled.
- Fast enough to feel like typing, not like submitting a job.
- Works across normal desktop apps, not just inside a browser extension.
- User-specific vocabulary matters: names, tools, projects, snippets, style.
- Keep architecture SaaS-ready without forcing SaaS complexity into the local MVP.

## Non-goals for the current MVP

- Billing, subscriptions, SSO, org admin, compliance paperwork.
- A polished marketing website.
- Team sync or multi-device sync.
- Cloud-first STT/LLM dependency.
- Complex plugin marketplace.
- Perfect voice command grammar.

## Core local modules

### Desktop shell

Responsible for lifecycle and Windows integration:

- Start app.
- Register global hotkey.
- Show minimal status/log output.
- Coordinate record/transcribe/process/paste.

### Audio recorder

Responsible for microphone capture:

- Start recording on command.
- Stop recording on command.
- Return temporary audio file or buffer.
- Avoid persistent audio unless explicit privacy setting allows it.

### STT adapter

Responsible for speech-to-text:

- Interface stays provider-neutral.
- Local provider path should support Whisper-family engines.
- Tests must not require heavy STT dependencies.
- Heavy deps are optional extras.

### Text processor

Responsible for turning transcript into intended text:

- Remove filler words.
- Handle simple corrections like “actually”, “sorry”, “I mean”.
- Normalize punctuation/capitalization.
- Apply local dictionary replacements.
- Expand snippets/commands.

### Local storage

Responsible for user configuration:

- SQLite for dictionary entries, snippets, settings, and optional events.
- Avoid storing raw transcripts/audio by default.
- Use simple schemas and migrations only when needed.

### Paste injector

Responsible for final insertion:

- Preserve existing clipboard when possible.
- Copy final text to clipboard.
- Trigger paste into focused app.
- Restore previous clipboard when safe.
- Fail gracefully with text still available.

## Future SaaS shape

When productizing later, keep the local app as the client and add services gradually:

- Account/device registry.
- Optional encrypted sync for dictionaries/snippets/settings.
- Optional cloud STT/LLM fallback.
- Usage analytics with privacy controls.
- Team vocabulary packs.
- Admin policy layer.
- Billing and licensing.

Do not add these before the local loop is excellent. Premature SaaS plumbing is how good tools become config museums.

## Coding rules

- Keep pure logic cross-platform and testable from Linux/WSL.
- Keep Windows-only behavior behind adapters.
- Prefer stdlib and small dependencies.
- No speculative abstractions.
- Product-original source, docs, prompts, UI, filenames, and public-facing text.
- No third-party assets, UI, marketing language, private APIs, or endpoint integrations.
- Every non-trivial change needs a runnable verification command.

## Current verification baseline

Expected from Windows repo root:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m fastwispr.cli process um meet at five actually six
.\.venv\Scripts\python.exe -m fastwispr.cli windows-smoke
```

Expected output characteristics:

- pytest passes.
- process command returns `Meet at six.`
- windows-smoke reports hotkeys/audio/paste imports as `ok`.
