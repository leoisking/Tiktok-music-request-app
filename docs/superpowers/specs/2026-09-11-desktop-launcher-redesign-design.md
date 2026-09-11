# Desktop Launcher Redesign — Design Spec

Date: 2026-09-11
Scope: `desktop_ui.py` (presentation layer), `desktop_branding.py` (icon color + `.ico` writer), `LiveWidget.ico`, `tests/test_desktop_ui.py`. `desktop_launcher.py` and `desktop_runtime.py` are unchanged.

## Goals

1. The launcher shares the overlays' visual identity (violet accent, deep navy surfaces, one type hierarchy).
2. Session state is shown once per region, and the primary action always matches the state.
3. A Home page gives a first-run user the whole picture: state, links, and what is left to set up.
4. Every hook the launcher code and the existing tests use keeps working.

## Palette

| Token | Value | Use |
| --- | --- | --- |
| BACKGROUND | `#0b0d12` | window |
| SIDEBAR | `#0e1118` | sidebar, footer |
| SURFACE | `#141822` | cards |
| SURFACE_2 | `#1a1f2b` | inputs, nested blocks, unselected tiles |
| BORDER | `#262c3a` | 1px rules |
| TEXT | `#f4f6fb` | primary text |
| MUTED | `#9aa3b5` | secondary text |
| ACCENT | `#8b7cff` | selection, focus, primary button |
| ACCENT_DARK | `#2a2650` | selected tile / nav background |
| ACCENT_TEXT | `#120e2e` | text on accent |
| SUCCESS | `#6fe3b4` | running state only |
| AMBER | `#f3ce8e` | warnings, unsaved |
| ERROR | `#ff9aa7` | errors, Stop button |
| ERROR_DARK | `#3a2230` | error notice / Stop button background |

Icon: `icon_png` bars change from mint `(128, 235, 197)` to violet `(139, 124, 255)`; plate stays dark. `build_icon_file(path)` writes a PNG-in-ICO with 16/32/48/64/256 frames; `LiveWidget.ico` is regenerated once and checked in. `write_windows_icon` still copies the checked-in file.

## Type

`display_font()` returns `'Segoe UI Variable Display'` if installed else `'Segoe UI'`; `text_font()` returns `'Segoe UI Variable Text'` else `'Segoe UI'`. Sizes: page title 22 bold (display), card title 12 bold (display), body 10, caption 9, eyebrow 8 bold, nav 10 bold.

## Structure

### Sidebar
Brand (icon 40px, "Live Widget", caption). Navigation without numbers: Home, Stream setup, Overlay links, Connections, Preferences. Selected item: ACCENT_DARK background, ACCENT text, 3px ACCENT left rule. Bottom: session pill (`self.session_pill`: dot canvas + label bound to `self.session_text`) and the `data_folder_button`.

### Header
`self.heading` and `self.description` only. The header badge is removed (`self.badge` no longer exists).

### Pages (`PAGES` order): `home`, `setup`, `overlays`, `connections`, `preferences`
- **home** (default page): 
  - Session card `self.session_card`: `self.session_headline` label (state), `self.session_detail` (mode · destination), `self.home_action` button mirroring the footer primary action (calls `app.start` or `app.stop` based on state), and `self.home_links` frame with three rows (label, readonly entry bound to `app.urls[name]`, Copy, Open). Copy/Open buttons are appended to `app.link_buttons`.
  - Checklist card: rows for chat source, overlay destination, Spotify; each row = status dot + title + `tk.StringVar` detail + "Go to" quiet button calling `show_page`. Details come from `refresh_settings`.
  - Tips card: three sentences on adding a Browser source in OBS / TikTok Studio.
- **setup**: cards "Chat source", "Overlay destination", "Private controls", "What happens next". Two-column ≥ 800px as today.
- **overlays**: as today plus `self.link_hints[name]` caption per card: skip "OBS: add a Browser source at 420 × 760 with a transparent background, or any size — the meter scales.", queue "OBS: add a Browser source at 520 × 860 (portrait) or 1280 × 720 (landscape). It fills whatever size you give it.", control "Open in your own browser only. Never add this page to a scene."
- **connections**, **preferences**: content unchanged, restyled; checkboxes become switches.

### Footer
`app.save_button` (quiet), `app.stop_button` (`Stop.TButton`: ERROR_DARK background, ERROR text), `app.start_button` (`Primary.TButton`). `set_session` shows exactly one of start/stop: `stopped`/`starting` → start visible (starting: disabled, text "Starting..."); `running`/`stopping` → stop visible (stopping: disabled, text "Stopping..."). Both widgets always exist.

### Switch widget
`class Switch(tk.Canvas)`: 44×24, pill track (SURFACE_2 off / ACCENT on), knob, focus ring in ACCENT, `<Button-1>`/`<space>`/`<Return>` toggle, redraws on variable change (trace). API: `configure(state='normal'|'disabled')` (also accepts other Canvas options), `instate(states)` → `'disabled' in states` iff disabled, `state(...)` no-op compat. Disabled: 45% dimmed colors, no toggling. Built by `_switch(parent, title, name)`, which packs a row with the switch and a clickable label.

## Behavior
- `refresh_settings` also updates: `session_detail`, checklist details, `home_action` text/state, `session_text`.
- `set_session(state)` updates: pill dot color + text, footer swap, `home_action`, `session_headline`, progress bar (as today).
- `links_ready` also fills/blanks the Home link rows (they share `app.urls`).
- `show_page` scrolls to top and masks secrets (as today).

## Verification
- `tests/test_desktop_ui.py`: all existing tests plus: default page is `home`; `set_session('running')` hides start and shows stop, `set_session('stopped')` reverses it; Switch reports `instate(['disabled'])` after `configure(state='disabled')` and ignores clicks; each overlay card has a non-empty hint; `LiveWidget.ico` bytes equal `build_icon_bytes()`.
- `tests/capture_desktop_ui.py` run; inspect `build/ui-preview/*.png` at 1120×820, 900×620, and 2× scaling.
