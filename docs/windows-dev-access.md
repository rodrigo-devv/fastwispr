# Windows Dev Access

## Current access

Friday can reach the Windows host over SSH through Tailscale MagicDNS:

```bash
ssh -i /opt/data/home/.ssh/fastwispr_windows_ed25519 w4rrior@godlike
```

Windows working tree:

```powershell
C:\development\fastwispr
```

This is enough for file sync, dependency install, unit tests, and non-GUI smoke checks.

## Why an interactive runner is needed

SSH sessions on Windows are not the same as Rodrigo's logged-in desktop session. Microphone, global hotkeys, focused-window paste, and app focus can behave differently or fail from an SSH service session.

For real desktop tests, start the dev runner from a normal PowerShell window inside the logged-in Windows desktop session.

## Start the interactive dev runner

From Windows PowerShell, not SSH:

```powershell
cd C:\development\fastwispr
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start-dev-runner.ps1
```

Leave that PowerShell window open while Friday runs tests.

The runner binds only to:

```text
127.0.0.1:8765
```

It uses a token stored at:

```powershell
$env:USERPROFILE\.fastwispr\dev-runner-token
```

Friday reaches it through an SSH tunnel, so no public firewall rule is needed.

## Agent-side tunnel

From Friday's environment:

```bash
ssh -i /opt/data/home/.ssh/fastwispr_windows_ed25519 \
  -o IdentitiesOnly=yes \
  -N -L 18765:127.0.0.1:8765 \
  w4rrior@godlike
```

Then local calls to `http://127.0.0.1:18765` hit the Windows interactive runner.

## Runner endpoints

All endpoints require:

```text
X-FastWispr-Dev-Token: <token>
```

- `GET /health` — confirms runner session and config.
- `GET /audio/devices` — lists Windows audio devices.
- `POST /process` — runs text cleanup pipeline.
- `POST /record-smoke` — records a short temp audio sample and deletes it after measuring bytes.
- `POST /paste` — pastes text into the currently focused Windows app. Use only when Rodrigo explicitly sets focus/approves the test.

## Safety

- The runner is loopback-only.
- Use SSH tunneling instead of opening a firewall port.
- Do not send secrets through paste tests.
- Do not trigger paste tests unless Rodrigo knows which app/window is focused.
