# FastWISPR — UI Design System / Visual Implementation Spec

## 1. Design Direction

Replicate the visual language of the approved FastWISPR reference design.

Core characteristics:

- Dark-first interface.
- Near-black backgrounds.
- Red as the primary accent and action color.
- White/light theme using the same structure and component geometry.
- Compact desktop application.
- Dense enough to feel like a real productivity tool, but never visually cluttered.
- Minimal, sharp, technical and premium.
- Avoid excessive rounded cards, glassmorphism, gradients, neon effects, oversized controls or decorative elements.
- Standard UI surfaces use subtle corner radii.
- The recording control is the exception: it is a fully rounded pill.

Visual priority:

1. Content
2. Clear hierarchy
3. Fast interaction
4. Subtle motion
5. Brand accent

---

# 2. Global Design Tokens

## Dark Theme

```css
:root {
  --bg: #090A0B;
  --surface: #111315;
  --surface-2: #17191C;
  --surface-hover: #1D2024;

  --border: #272A2E;
  --border-hover: #363A40;

  --text: #F5F5F5;
  --text-secondary: #A1A1AA;
  --text-muted: #71717A;

  --accent: #E10600;
  --accent-hover: #FF1A14;
  --accent-soft: rgba(225, 6, 0, 0.12);

  --success: #22C55E;
  --warning: #F59E0B;
  --error: #EF4444;

  --overlay: rgba(0, 0, 0, 0.72);

  --radius-xs: 3px;
  --radius-sm: 5px;
  --radius-md: 7px;
  --radius-lg: 9px;
  --radius-pill: 999px;

  --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.22);
  --shadow-md: 0 8px 28px rgba(0, 0, 0, 0.32);
}
```

## Light Theme

```css
[data-theme="light"] {
  --bg: #FFFFFF;
  --surface: #F7F7F7;
  --surface-2: #F0F0F0;
  --surface-hover: #EAEAEA;

  --border: #E2E2E2;
  --border-hover: #D2D2D2;

  --text: #111111;
  --text-secondary: #5F6368;
  --text-muted: #858585;

  --accent: #D60000;
  --accent-hover: #E10600;
  --accent-soft: rgba(214, 0, 0, 0.08);

  --success: #16A34A;
  --warning: #D97706;
  --error: #DC2626;

  --overlay: rgba(0, 0, 0, 0.42);
}
```

---

# 3. Typography

Use a clean modern sans-serif.

Preferred:

```css
font-family: "Inter", "Segoe UI", sans-serif;
```

Optional display/accent font:

```css
font-family: "Space Grotesk", "Inter", sans-serif;
```

Technical metadata:

```css
font-family: "JetBrains Mono", monospace;
```

## Sizes

```css
--text-xs: 11px;
--text-sm: 12px;
--text-md: 13px;
--text-lg: 14px;
--text-xl: 16px;
--text-2xl: 20px;
```

Recommended weights:

- 400 — normal body text
- 500 — labels and secondary controls
- 600 — section titles and important values
- 700 — rare emphasis only

Avoid oversized typography.

---

# 4. Main Application Window

The main application is a compact desktop hub.

Recommended default dimensions:

```css
width: 400px;
height: 560px;
min-width: 380px;
min-height: 520px;
max-width: 460px;
max-height: 620px;
```

Position:

- Bottom-right area of the primary/active monitor.
- Slightly above the Windows taskbar.
- The window should visually feel connected to the system tray area.
- It should not touch the screen edge.
- Horizontal margin: approximately 16–24px.
- Bottom margin: approximately 12–20px above the taskbar.

## Window

```css
.app-window {
  background: var(--bg);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}
```

Do not use:

- giant 24px+ corner radii
- glass blur
- transparent floating cards
- colorful gradients

---

# 5. Application Header

Compact horizontal header.

Structure:

```text
[ FastWISPR ]                         [ theme ] [ menu ]
```

Characteristics:

- Height: 48–54px.
- Logo/name aligned left.
- Utility buttons aligned right.
- Bottom border may be used.
- No giant branding.

```css
.app-header {
  height: 52px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
}

.brand {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.brand-accent {
  color: var(--accent);
}
```

---

# 6. Navigation

Use a compact navigation system.

Possible structure:

```text
Home
History
Dictionary
Snippets
Settings
```

Navigation should feel like a productivity application, not a website.

Active item:

```css
.nav-item.active {
  background: var(--accent-soft);
  color: var(--text);
}

.nav-item.active .icon {
  color: var(--accent);
}
```

Dimensions:

- Height: 32–36px.
- Horizontal padding: 10–12px.
- Radius: 5–7px.
- Icon: approximately 16px.
- Text: 12–13px.

Avoid oversized sidebar navigation.

---

# 7. Home Screen

The Home screen is intentionally minimal.

Visual hierarchy:

```text
FastWISPR
Ready

Microphone
Default Microphone

Model
Selected Model

Shortcut
Ctrl + Space

Recent activity
----------------
Transcript
Transcript
Transcript
```

Do not turn Home into a dashboard full of statistics.

## Status

Primary state:

```css
.status {
  font-size: 20px;
  font-weight: 600;
}

.status.ready {
  color: var(--text);
}

.status.recording {
  color: var(--accent);
}
```

Supporting status text:

```css
.status-description {
  color: var(--text-secondary);
  font-size: 12px;
}
```

---

# 8. Setting Rows

Use compact horizontal rows instead of large cards.

```text
Microphone             Default Microphone   >
Model                  Whisper Large        >
Language               Auto                  >
Shortcut               Ctrl + Space         >
```

```css
.setting-row {
  min-height: 46px;
  padding: 8px 12px;

  display: flex;
  align-items: center;
  justify-content: space-between;

  border: 1px solid var(--border);
  background: var(--surface);

  border-radius: var(--radius-sm);
}

.setting-row:hover {
  background: var(--surface-hover);
  border-color: var(--border-hover);
}
```

Do not make every setting a large rounded card.

---

# 9. Buttons

## Primary Button

Used for the main action.

```css
.button-primary {
  background: var(--accent);
  color: #FFFFFF;
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  min-height: 34px;
  padding: 0 14px;
  font-size: 12px;
  font-weight: 600;
}

.button-primary:hover {
  background: var(--accent-hover);
}
```

## Secondary Button

```css
.button-secondary {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  min-height: 34px;
  padding: 0 14px;
}
```

## Ghost Button

```css
.button-ghost {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
}

.button-ghost:hover {
  background: var(--surface-hover);
  color: var(--text);
}
```

Buttons should be compact and rectangular with subtle rounding.

---

# 10. Icon Buttons

Small square controls.

```css
.icon-button {
  width: 32px;
  height: 32px;

  display: flex;
  align-items: center;
  justify-content: center;

  background: transparent;
  color: var(--text-secondary);

  border: 1px solid transparent;
  border-radius: var(--radius-sm);
}

.icon-button:hover {
  background: var(--surface-hover);
  color: var(--text);
}

.icon-button.danger:hover {
  color: var(--accent);
  background: var(--accent-soft);
}
```

Icon size:

```css
width: 15px;
height: 15px;
```

Use simple line icons.

---

# 11. History

History is a clean chronological list.

Example:

```text
Today

09:42
This is the transcript text...

09:18
Another transcription...

Yesterday

18:32
Previous transcript...
```

Each row should be compact.

```css
.history-item {
  padding: 12px;
  border-bottom: 1px solid var(--border);
}

.history-item:hover {
  background: var(--surface);
}
```

Metadata:

```css
.history-time {
  color: var(--text-muted);
  font-size: 11px;
}

.history-text {
  color: var(--text);
  font-size: 13px;
  line-height: 1.45;
}
```

Actions should appear subtly on hover:

```text
Copy   Edit   Retry   Delete
```

Do not permanently display four large action buttons on every row.

---

# 12. Transcript Detail

When a transcript is opened:

```text
09:42
--------------------------------
Transcript text...

[ Copy ] [ Edit ]
```

Transcript container:

```css
.transcript {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px;
  line-height: 1.55;
}
```

Primary action:

```css
.copy-button {
  background: var(--accent);
  color: white;
}
```

Copy feedback should be immediate and subtle:

```text
Copied
```

Do not use large modal dialogs for simple copy actions.

---

# 13. Recording Overlay — Signature Component

This is the most visually important component.

The recording interface is a floating pill independent from the main application window.

It should appear near the top-center of the active monitor.

Example:

```text
┌─────────────────────────────────────┐
│  ●  ▂ ▅ ▇ ▅ ▂ ▃ ▆ ▄       00:04     │
└─────────────────────────────────────┘
```

It must feel lightweight and native to the desktop.

## Geometry

```css
.recording-pill {
  height: 38px;
  min-width: 140px;
  padding: 0 13px;

  border-radius: 999px;

  background: #111315;
  border: 1px solid #272A2E;

  box-shadow:
    0 8px 30px rgba(0,0,0,.30),
    0 0 0 1px rgba(255,255,255,.02);
}
```

The pill itself is the only intentionally fully-rounded major component.

---

# 14. Recording Pill — Left Indicator

A small red recording indicator.

```css
.recording-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
}
```

During recording:

- subtle opacity/pulse
- never an aggressive flashing animation

Suggested pulse:

```text
opacity: 1 → .55 → 1
duration: ~1000ms
```

---

# 15. Recording Waveform

Use approximately 7–15 vertical bars.

Example:

```text
▂ ▅ ▇ ▆ ▃ ▅ ▂ ▆ ▄
```

Characteristics:

- Bars respond to real microphone amplitude when available.
- Motion is smooth rather than jittery.
- Red is reserved for the active recording accent.
- Secondary bars can use muted/light values.
- The waveform should remain compact.

```css
.waveform {
  display: flex;
  align-items: center;
  gap: 2px;
  height: 20px;
}

.waveform-bar {
  width: 2px;
  min-height: 3px;
  max-height: 17px;
  border-radius: 2px;
  background: var(--accent);
}
```

Do not use a large audio visualizer.

---

# 16. Recording Timer

Timer is secondary information.

```css
.recording-time {
  font-family: "JetBrains Mono", monospace;
  font-size: 11px;
  color: var(--text-secondary);
  min-width: 34px;
  text-align: right;
}
```

Example:

```text
00:04
```

---

# 17. Recording Pill States

## Recording

```text
●  waveform                 00:04
```

Visual:

- Red recording dot.
- Animated waveform.
- Timer.
- Dark background.
- Subtle shadow.

## Processing

Replace waveform with a restrained processing indicator.

```text
●  Processing...
```

Do not use a large spinner.

## Success

Brief success state:

```text
✓  Done
```

Success may use `--success`.

The state should remain visible only briefly before the pill exits.

## Error

```text
!  Couldn't transcribe
```

Use `--error`.

Keep the pill visible slightly longer.

Optional action:

```text
Retry
```

---

# 18. Recording Pill Entry Animation

The pill must originate outside the right edge of the screen.

Initial state:

```text
screen right edge
                         [PILL]
                         ↑ completely outside
```

Then:

```text
                         [PILL]
                       →→→→→→→
```

Final:

```text
                 [● waveform 00:04]
```

Animation:

```css
transform: translateX(calc(100% + 24px));
opacity: 0;
```

to:

```css
transform: translateX(0);
opacity: 1;
```

Recommended duration:

```text
180–260ms
```

Easing:

```text
OutCubic
```

or a very subtle spring.

Do not make it bounce heavily.

---

# 19. Recording Pill Exit Animation

After processing/success:

```text
[PILL] →→→→→→→ outside screen
```

Duration:

```text
150–220ms
```

Use an accelerated ease-in.

The exit should feel like the same component reversing its entrance.

---

# 20. Overlay Position

Default position:

```text
Top center
```

Recommended:

```css
top: 24px;
```

Center horizontally against the active monitor.

The overlay must remain above normal application windows.

It should not steal keyboard/mouse focus.

It should be visually independent of the main FastWISPR window.

---

# 21. Status Indicators

Use tiny status indicators.

```css
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
```

States:

```text
Ready       neutral
Recording   red
Processing  amber/neutral
Success     green
Error       red
```

Avoid large colored badges.

---

# 22. Cards / Surfaces

Cards are allowed but should be restrained.

```css
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
}
```

Rules:

- Use cards to group information.
- Do not nest cards inside cards.
- Do not make every row a card.
- Avoid floating-card-heavy layouts.

---

# 23. Dividers

```css
.divider {
  height: 1px;
  background: var(--border);
}
```

Use subtle dividers for:

- sections
- history grouping
- settings
- header boundaries

Avoid heavy separators.

---

# 24. Inputs

```css
.input {
  height: 34px;
  padding: 0 10px;

  background: var(--surface);
  color: var(--text);

  border: 1px solid var(--border);
  border-radius: var(--radius-sm);

  outline: none;
}

.input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-soft);
}
```

Inputs should look compact and professional.

---

# 25. Dropdowns

```css
.select {
  min-height: 34px;
  padding: 0 10px;

  background: var(--surface);
  color: var(--text);

  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}
```

Do not use oversized modern mobile-style dropdowns.

---

# 26. Toggles

Minimal compact toggle.

```text
OFF   [────]
ON    [●───]
```

Active state uses the red accent.

The toggle should be approximately:

```text
34 × 18px
```

---

# 27. Tooltips

Use small dark tooltips.

```css
.tooltip {
  background: #111315;
  color: #F5F5F5;
  border: 1px solid #272A2E;
  border-radius: 4px;
  padding: 5px 7px;
  font-size: 11px;
}
```

Only show when the user hovers an icon whose meaning is not obvious.

---

# 28. Context Menus / Tray Menu

Compact native-looking menu.

Example:

```text
FastWISPR

Start recording
Open FastWISPR
Copy last transcript

----------------

Settings
Quit
```

Style:

```css
.context-menu {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  padding: 4px;
}

.context-item {
  height: 30px;
  padding: 0 9px;
  border-radius: 4px;
  font-size: 12px;
}
```

Hover:

```css
.context-item:hover {
  background: var(--surface-hover);
}
```

---

# 29. Notifications / Toasts

Small, unobtrusive notifications.

Example:

```text
✓ Transcript copied
```

Geometry:

- 280px maximum width.
- 32–40px height.
- 8px radius.
- Bottom-right placement.
- Small shadow.

Do not use huge notification banners.

---

# 30. Empty States

Empty states should contain:

1. Small icon
2. Short title
3. One-line explanation
4. Optional action

Example:

```text
          ◌

       No history yet

   Your transcriptions will appear here.

       [ Start recording ]
```

Keep empty states visually quiet.

---

# 31. Loading States

Avoid large spinners.

Preferred:

- subtle three-dot animation
- compact spinner
- skeleton rows only when loading a substantial list

Example:

```text
Transcribing...
```

with a small animated indicator.

---

# 32. Spacing System

Use a strict spacing scale:

```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
```

Most UI should use:

- 8px
- 12px
- 16px

Avoid arbitrary spacing values.

---

# 33. Borders

Borders should be visible but subtle.

Dark:

```css
border: 1px solid #272A2E;
```

Hover:

```css
border-color: #363A40;
```

Accent/focus:

```css
border-color: var(--accent);
```

Never use thick 2–3px borders for normal controls.

---

# 34. Shadows

Shadows should create depth without looking like floating glass.

Primary:

```css
box-shadow: 0 8px 28px rgba(0,0,0,.32);
```

Small:

```css
box-shadow: 0 2px 8px rgba(0,0,0,.22);
```

Avoid exaggerated shadows.

---

# 35. Light Theme Rules

The light theme is structurally identical to the dark theme.

Do not redesign the UI for light mode.

Only change:

- backgrounds
- surfaces
- borders
- text
- accent intensity
- shadows

The red accent remains the brand identifier.

The result should feel like the same application, not a separate theme.

---

# 36. Dark Theme Rules

Dark mode is the primary visual identity.

Important:

- Background should be near-black, not blue-gray.
- Surfaces should be only slightly lighter than the background.
- Red should appear selectively.
- White text should not be pure white everywhere.
- Secondary text should be visibly dimmer.
- Borders should be subtle.

Red should communicate:

- recording
- primary actions
- active navigation
- focus
- brand identity
- errors only when appropriate

Do not paint entire components red.

---

# 37. Component Radius Rules

Use this hierarchy:

```text
Normal window       7–9px
Cards                7px
Inputs               5px
Buttons              5px
Icon buttons         5px
Menus                7px
Recording overlay    999px
Status dots          50%
```

The recording pill is intentionally the only major fully-pill-shaped component.

---

# 38. Motion System

Motion should communicate state, not decorate the interface.

Fast interactions:

```text
120–160ms
```

Normal transitions:

```text
160–220ms
```

Recording pill entrance:

```text
180–260ms
```

Recording pill exit:

```text
150–220ms
```

Hover:

```text
100–140ms
```

Avoid:

- large bounces
- spinning decorative objects
- long page transitions
- excessive parallax
- constant animations

---

# 39. Visual Hierarchy

Every screen should have:

```text
Primary
↓
Secondary
↓
Metadata
↓
Actions
```

Example:

```text
This is the transcript
    Today, 09:42
    14 seconds

                         Copy
```

Primary text should always be visually stronger than metadata.

---

# 40. Overall Visual Test

The finished UI should look like:

- a serious desktop productivity application
- compact
- fast
- technically polished
- intentionally designed
- native enough to belong on Windows
- visually distinctive because of the black/red identity
- calm when idle
- immediately recognizable when recording

The signature interaction is:

```text
IDLE
     ↓
[PILL ENTERS FROM RIGHT]
     ↓
[● WAVEFORM 00:04]
     ↓
[PROCESSING]
     ↓
[✓ DONE]
     ↓
[PILL EXITS TO RIGHT]
```

That recording interaction must receive the highest visual polish.

---

# 41. Design Don'ts

Do NOT introduce:

- giant microphone buttons
- giant rounded cards
- excessive 20–32px corner radii
- glassmorphism
- translucent acrylic everywhere
- neon cyberpunk styling
- excessive gradients
- giant dashboards
- excessive statistics
- huge empty spaces
- oversized typography
- animated backgrounds
- decorative particles
- excessive shadows
- colorful rainbow accents
- mobile-app-looking controls
- excessive modals
- unnecessary confirmation dialogs

The intended feeling is:

**Minimal, not empty.  
Premium, not flashy.  
Technical, not cold.  
Fast, not chaotic.**
