# Desktop Launcher Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle and restructure the tkinter launcher to match the overlays (violet/navy), add a Home page, unify session state, and swap Start/Stop by state, without breaking any launcher or test hook.

**Architecture:** All presentation stays in `desktop_ui.py` (`LauncherView`), icon generation in `desktop_branding.py`. `desktop_launcher.py` keeps calling the same view methods. New `Switch` canvas widget mimics the ttk state API so the existing lock/unlock tests work unchanged.

**Tech Stack:** Python 3.14, tkinter/ttk (clam theme), stdlib PNG/ICO writers.

**Spec:** `docs/superpowers/specs/2026-09-11-desktop-launcher-redesign-design.md`

**Status (2026-09-11):** All three tasks implemented and verified in-session (27 launcher tests, 118 total, screenshots for every page and state via `tests/capture_desktop_ui.py`, which now also captures the running Home page). Git is unavailable on this machine, so no commits were made.

## Global Constraints

- Keep every attribute listed in the spec's "What stays fixed" (see spec Structure/Behavior). `initial_window_geometry` unchanged.
- Fonts via `display_font()` / `text_font()` with Segoe UI fallback; never hard-code a font that may be missing.
- Run tests with `.venv/Scripts/python.exe -m unittest tests.test_desktop_ui`. Git unavailable: no commits.

---

### Task 1: Branding — violet icon and `.ico` writer

**Files:** Modify `desktop_branding.py`, `LiveWidget.ico` (regenerated), `tests/test_desktop_ui.py`.

- [ ] Write failing test: `build_icon_bytes()` starts with the ICO header `b'\x00\x00\x01\x00\x05\x00'` and `LiveWidget.ico` bytes equal `build_icon_bytes()`.
- [ ] Run: FAIL (`build_icon_bytes` missing).
- [ ] Implement `ACCENT_RGB = (139, 124, 255)` in `icon_png`, `build_icon_bytes(sizes=(16, 32, 48, 64, 256))` producing PNG-in-ICO, `build_icon_file(path)`.
- [ ] Regenerate: `python -c "from desktop_branding import build_icon_file; build_icon_file('LiveWidget.ico')"`.
- [ ] Run tests: PASS.

### Task 2: Launcher view rewrite

**Files:** Rewrite `desktop_ui.py`; extend `tests/test_desktop_ui.py`.

- [ ] Write failing tests: default page `home`; `set_session('running')` → `start_button.winfo_manager() == ''` and `stop_button.winfo_manager() != ''`, reversed after `set_session('stopped')`; `Switch.configure(state='disabled')` → `instate(['disabled'])` true and click leaves the variable unchanged; `link_hints` has a non-empty hint for all three link names; `session_text` contains "Not running" initially and "Running" after `set_session('running')`.
- [ ] Run: FAIL.
- [ ] Rewrite `desktop_ui.py` per spec (palette, fonts, Switch, sidebar pill, Home page, footer swap, overlay hints, restyled pages).
- [ ] Run `tests.test_desktop_ui`: all PASS. Run full suite: only known-good state.
- [ ] Run `tests/capture_desktop_ui.py` and inspect every PNG; fix clipping or contrast issues found.

### Task 3: Docs

- [ ] CHANGELOG entry under "Desktop application"; DISTRIBUTION.md "Using the desktop interface" paragraph updated for Home page and session button.
