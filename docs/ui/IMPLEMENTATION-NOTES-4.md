# FastWISPR — PySide6 implementation handoff

For the coding agent implementing the approved UI in https://github.com/rodrigo-devv/fastwispr

This replaces the current `tkinter` settings window and the thin `pystray` menu with a compact Qt hub. Do not add a browser, Electron, or QWebEngine to render the designs.

Design source of truth:

- Design system: `/workspace/fastwispr-design/.superdesign/design-system.md`
- Superdesign canvas: https://superdesign.dev/teams/8e1954e9-46f0-4d3c-b327-533cf25b8856/projects/79233285-34fe-4b9b-9671-98bf5dc90d00
- Home (approved v2): draft `690e13e4-0893-417c-9f0b-93793f9874d8`
- Desktop placement: draft `7dd23949-d4b7-47c5-bf12-9f7f0d21b507`
- Overlay storyboard: draft `8374780b-4c3a-4b62-9e92-9f060b0bfa3b`

HTML drafts are visual contracts, not markup to embed. Rebuild with `QWidget` + QSS.

---

## 1. Product constraints (do not invent)

Real today:

- Local `faster-whisper`. Presets: Fast = `base`, Balanced = `small`, Accurate = `medium`. All CPU / int8.
- Default hotkey: **Ctrl+Space** toggle. Mouse 4 hold-to-talk is a fallback, not the Home hint.
- Language default `pt-en`. Also `pt-BR`, `en`.
- Dictionary and snippets already exist (CLI + config).
- History is optional local SQLite. Raw audio / raw transcripts off by default.
- No account, no cloud STT, no LLM rewrite.

UI copy: English. Wordmark: `Fast` in primary text + `WISPR` in accent red. Never `FASTWISPR`.

---

## 2. Window

| | px |
|---|---|
| Default | 400 × 560 |
| Min | 380 × 520 |
| Max | 460 × 620 |

Placement (approved):

- Active monitor that owns the tray / taskbar. Do not assume primary.
- Right inset **20px**
- Bottom inset **16px above the taskbar** (not the screen edge)
- Never centered. Never top-left. Never maximized. No maximize button.

Use `QScreen.availableGeometry()` (excludes taskbar) then:

```text
x = avail.right() - width - 20
y = avail.bottom() - height - 16
```

DPI: multiply insets by `devicePixelRatio` only if you are in physical pixels. `availableGeometry()` is already in Qt logical pixels — keep 20 / 16 in logical px.

Open animation (optional): opacity 0→1, `y += 8` → 0, 120–160ms. Anchor to the tray, not a bounce.

### Chrome

Frameless `Qt.FramelessWindowHint` + `Qt.Window`. Custom title bar, height **52**.

Left: wordmark `FastWISPR` (14 / 600, tracking −0.02em).

Right, in this order:

1. Theme toggle 32×32, radius 5
2. 1px divider
3. Minimize 40×52, flush caption style
4. Close 40×52, hover fill `accent-soft`, icon accent

No maximize. Drag the title bar to move. Double-click title bar does nothing.

Inner screens keep this chrome and add a **44px page bar** under it: back · title · optional primary (Add). Do not put back or Add in the window chrome.

---

## 3. Tokens → QSS

Dark is default. Light and System are required. Live switch, no restart.

```css
/* dark */
QWidget#AppShell {
  background: #090A0B;
  color: #F5F5F5;
  border: 1px solid #272A2E;
  border-radius: 9px;
}
```

| Role | Dark | Light |
|---|---|---|
| bg | `#090A0B` | `#FFFFFF` |
| surface | `#111315` | `#F7F7F7` |
| surface-hover | `#1D2024` | `#EAEAEA` |
| border | `#272A2E` | `#E2E2E2` |
| text | `#F5F5F5` | `#111111` |
| text-secondary | `#A1A1AA` | `#5F6368` |
| text-muted | `#71717A` | `#858585` |
| accent | `#E10600` | `#D60000` |
| accent-hover | `#FF1A14` | `#E10600` |
| accent-soft | `rgba(225,6,0,0.12)` | `rgba(214,0,0,0.08)` |
| success | `#22C55E` | `#16A34A` |
| warning | `#F59E0B` | `#D97706` |
| error | `#EF4444` | `#DC2626` |

Radius: window 9, cards/menus 7, inputs/buttons/rows 5, overlay 999, dots 50%.

Spacing scale: 4 / 8 / 12 / 16 / 20 / 24 / 32. Page pad 16. Row pad 12. Section gap 20–24.

Type:

- UI: Inter if you bundle it; else **Segoe UI** (already on Windows). Do not ship a web font loader.
- Mono: JetBrains Mono if bundled; else **Cascadia Mono** / Consolas.
- Sizes: 11 caption/timer, 12 secondary/buttons, 13 body, 14 chrome/section, 20 Home status.
- Weights: 400 / 500 / 600. Almost never 700.

Focus: 1px accent + 2px accent-soft. Qt: `outline` is weak — use a `QProxyStyle` or a 2px border on `:focus`.

Shadow: `QGraphicsDropShadowEffect` on the window (blur 28, offset 0,8, color `#00000052`). No glow.

---

## 4. Navigation

One `QStackedWidget` inside `AppShell`.

```
Home
History → TranscriptDetail
Dictionary
Snippets
Settings → SpeechRecognition (and later: General, Dictation, Microphone, Privacy, Shortcuts, Appearance, About)
```

Home footer: History (secondary) + Settings (primary red).

Home config chips open Speech recognition and Microphone. Microphone settings page may be a later slice; the chip can open Settings scrolled to that row until the page exists.

No website sidebar. No hamburger.

---

## 5. Home (approved)

Centered status: 6px muted dot + `Ready` 20/600.

Hint: `Hold` + keycaps `Ctrl` `Space` + `to dictate`. Keycap: 20h, pad 6, radius 5, surface + border, JetBrains 11.

Two chips, 46h, radius 5, chevron-right: Model `whisper-small` · Microphone `Default`. Show the **selected** model id, not a fake `whisper-large-v3`.

Recent: 3 rows. Transcript 13, metadata 11 muted (`Today · 13:42 · 4.8s`). Copy icon **always visible** (28px), not hover-only.

Footer 34h buttons.

Status colors: Ready muted/text · Recording accent · Processing warning · Error error.

---

## 6. History / detail / empty

Search field 34h. Group Today / Yesterday / date. Row: text + `13:42 · 4.8s` + Copy.

Click row → Transcript detail:

- Readable text in a surface panel, radius 7, pad 14, line-height ~1.55
- Metadata: When, Duration, Model (`Balanced · whisper-small`)
- Footer: Copy (primary) · Edit · Retry

Empty: clock icon 22, `No transcriptions yet`, `Hold Ctrl+Space and start speaking.`, `Try a test` (starts a recording or focuses the hint — do not invent a tutorial).

Copy feedback: tiny toast `✓ Copied`. No modal.

---

## 7. Dictionary / Snippets

Same chrome + page bar + Add (primary, in the page bar).

Dictionary: spoken → written list. Sample rows may use real CLI examples (`tail scale` → `Tailscale`). Search on top.

Snippets: name + expansion. Click opens a small editor (plain `QPlainTextEdit`, not a web editor).

---

## 8. Settings / Speech recognition

Settings is a vertical list of rows (46h), not a dashboard.

Rows that exist in the product: General, Dictation, Microphone, Speech recognition, Privacy, Shortcuts, Appearance, About.

Speech recognition (built):

- Preset segmented: Fast | **Balanced** | Accurate
- Read-only facts for the selected preset: Model, Language, Device, Compute
- Caption: `Local faster-whisper. First run may download the model if it is not cached. No audio leaves the machine.`

Privacy shows facts that exist: audio retention off by default, history optional, processing is local. **Do not add a Cloud processing toggle.**

Appearance: Dark / Light / System. Default Dark.

---

## 9. Overlay — highest polish

Separate `QWidget` window:

- `Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint`
- `Qt.WA_TranslucentBackground` + `Qt.WA_ShowWithoutActivating`
- Does **not** steal focus. `Qt.WindowDoesNotAcceptFocus` if the Qt version supports it.
- Height 38, min-width 140, pad 0 13, radius 999, surface `#111315`, border `#272A2E`
- Position: **top-center of the active monitor**, `top = 24`

States:

| State | Content |
|---|---|
| Idle | Usually hidden. Optional Ready + Ctrl+Space (desktop mock only) |
| Recording | 7px accent dot (pulse opacity 1→0.55, 1000ms) · 7–15 bars · `00:04` mono 11 |
| Processing | small spinner + `Transcribing…` |
| Success | green check + `Done` · brief · exit |
| Error | `Couldn't transcribe` + Retry · stays longer · click opens History |

Waveform: 2×3–17 bars, gap 2, radius 2, accent. Drive from real RMS when available. Smooth, not a DJ EQ.

### Motion

Enter from **fully outside the right edge**:

```text
start: x = screen.right + width + 24, opacity 0
end:   x = (screen.width - pill.width) / 2, y = 24, opacity 1
180–260ms, OutCubic (QEasingCurve.OutCubic)
```

Exit: reverse, 150–220ms, InCubic. No bounce.

`QPropertyAnimation` on `pos` + `windowOpacity`. One animation group.

---

## 10. Tray / paste / toast

`QSystemTrayIcon`. Icon: geometric red dot on near-black, same family as the window (do not mix Windows stock icons).

Menu (30h rows, radius 4, 12px):

```
FastWISPR                         Ready
Start recording                   Ctrl+Space
Copy last transcript
Open FastWISPR
History
Settings
—
Pause hotkeys
Start with Windows
Quit
```

Clicking the tray icon opens the hub at the approved position.

Paste failed: compact card, not a `QMessageBox`.

```
Paste failed
Your transcript is safe.
[ Copy ] [ Retry ]
```

Toast: max 280×40, radius 8, bottom-right near the hub. 180ms in.

---

## 11. Qt mapping

| Design | Qt |
|---|---|
| AppShell | `QWidget` frameless + shadow effect |
| TitleBar | custom `QWidget`, `mousePress/Move` for drag |
| Page bar | `QHBoxLayout` 44h |
| Stack | `QStackedWidget` |
| SettingRow / chips | `QPushButton` or `QFrame` + click |
| Search | `QLineEdit` |
| History list | `QListView` + model, or `QScrollArea` of rows |
| Toggle | custom 34×18, accent when on |
| Overlay | second `QWidget`, tool window |
| Waveform | `QWidget.paintEvent` bars |
| Tray | `QSystemTrayIcon` + `QMenu` styled |
| Toast | `QWidget` tool, no focus |

Icons: one Lucide-style set (SVG). 15px in 32px buttons. Bundle SVGs. No emoji.

Fonts: add via `QFontDatabase.addApplicationFont` if you ship Inter / JetBrains. Otherwise Segoe UI + Cascadia Mono.

Do **not** use:

- `QWebEngineView` to paint the Superdesign HTML
- Acrylic / `QtWin.Dwm` blur
- 20–32px radii
- Giant circular mic button
- Hover-only Copy as the only path (context menu + shortcut required)

---

## 12. Acceptance

- [ ] Hub opens on tray click at 20px / 16px on the tray's monitor
- [ ] No maximize; min/max size honored
- [ ] Dark / Light / System switch live
- [ ] Home shows Ctrl+Space and the real selected model
- [ ] Dictate works with the hub closed; overlay does not steal focus
- [ ] Overlay enters from the right, exits to the right
- [ ] Failed paste never loses text
- [ ] Dictionary / snippets / history persist as they do today
- [ ] Light theme is the same geometry, not a restyle

If a Qt effect is ugly (rounded frameless shadow on Windows), drop the shadow before faking glass. Implementability + polish beats pixel-perfect CSS.
