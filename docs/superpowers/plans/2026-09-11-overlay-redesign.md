# Overlay and Control Panel Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the two on-stream overlays and the control panel into one calm "album-art glass" system without changing behavior, ids, or the browser-test contracts.

**Architecture:** Pure front-end change to two self-contained HTML files (`index.html`, `queue_widget.html`); all CSS and JS stay inline because the server hashes inline scripts for CSP and has no static route. Verification uses a new Python harness that drives headless Microsoft Edge over the Chrome DevTools Protocol (CDP) with a stdlib-only WebSocket client, since Node/Playwright is not installed.

**Tech Stack:** HTML/CSS/vanilla JS, Socket.IO client 4.0.1 (CDN), Google Fonts (Plus Jakarta Sans, Inter), Flask test server via werkzeug, Microsoft Edge headless, Python 3.14 stdlib.

**Spec:** `docs/superpowers/specs/2026-09-11-overlay-redesign-design.md`

**Status (2026-09-11):** All five tasks implemented and verified in-session. Tasks 3 and 4 were executed as one pass because both live in `index.html`. Two extras surfaced during execution and were fixed: the skip meter no longer plays its "new vote" effects on the first state sync after connecting, and moderator actions use a plain `socket.emit` because `volatile.emit` dropped the second of two quick clicks. Git is unavailable on this machine, so no commits were made.

## Global Constraints

- No backend changes; `live_widget.py` is not modified. No new URL parameters.
- CSP: inline `<script>` blocks are hashed automatically; styles may be inline; fonts only from `fonts.googleapis.com`/`fonts.gstatic.com`; images `https:`; scripts also from `cdnjs.cloudflare.com`.
- Every id, class hook, and global listed in the spec's "contracts" must keep existing and behaving.
- Default `/` overlay: transparent `html`, `body`, `#voting-panel`; `#voting-panel` has `box-shadow: none` and `backdrop-filter: none`; `.requests-panel` has `hidden-panel` until enabled; `.border-glow` and `.glow-line` inside `#voting-panel` are not visible; `#particles` is not visible; `#skip-count` has a non-`none` `text-shadow`.
- `/control` and `?bg=black`: `body` background `rgb(0, 0, 0)`; `#voting-panel` background not transparent.
- `.request-item img` count must be 0 for items without `album_art`.
- No horizontal overflow at widths 320, 375, 768 on any page.
- Skip meter content (`.skip-command-hint`, `#skip-meter-circle`, `#skip-count`) fits inside `#voting-panel` and inside 200×200, 320×240, 1920×1080 sources; pixel (100,190) of a 200×200 transparent render stays alpha 0.
- Fonts: Plus Jakarta Sans 600/700/800 for display and numbers; Inter 500/600 for body. No other families.
- Motion removed per spec; `prefers-reduced-motion: reduce` disables all animation/transition.
- Run tests with `.venv/Scripts/python.exe` from the repo root. Git is not available: skip commit steps and instead note completion in the plan checkboxes.

---

### Task 1: Headless Edge verification harness

**Files:**
- Create: `tests/edge_overlay_check.py`
- Modify: `README.md` (Test section, add the Edge check command)

**Interfaces:**
- Produces: CLI `python tests/edge_overlay_check.py [--screenshots DIR] [--port N]` exiting 0 on success. Internal API used by later tasks: `Edge.goto(url)`, `Edge.evaluate(js)`, `Edge.set_viewport(w, h)`, `Edge.screenshot(path, omit_background=False)`, `Edge.new_page()`.
- Consumes: `live_widget.app` and state globals for seeding (`song_queue`, `now_playing_state`, `skip_votes`, `spotify_queue_state`, `spotify_queue_status`, `visibility_state`, `state_lock`).

- [ ] **Step 1: Write the harness skeleton with one failing check**

Create `tests/edge_overlay_check.py`:

```python
"""Headless-Edge checks for the overlay pages when Node/Playwright is unavailable.

Usage:
    python tests/edge_overlay_check.py [--screenshots DIR] [--port 5077] [--debug-port 9333]
    python tests/edge_overlay_check.py --serve 5077   # internal: seeded test server
"""
import argparse
import base64
import json
import os
import secrets
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
ART = "https://i.scdn.co/image/ab67616d0000b273e8b066f70c206551210d902b"
PASSWORD = "edge-check-only-password"


def find_edge():
    for path in EDGE_PATHS:
        if os.path.exists(path):
            return path
    raise SystemExit("Microsoft Edge not found; install Edge or run tests/test_overlays.cjs with Node.")


# ----------------------------------------------------------------------------- seeded server
def serve(port):
    os.environ.update({
        "CONTROL_PASSWORD": PASSWORD, "ALLOWED_ORIGINS": "",
        "SPOTIFY_CLIENT_ID": "", "SPOTIFY_CLIENT_SECRET": "", "SPOTIFY_REFRESH_TOKEN": "",
        "SPOTIFY_QUEUE_ON_REQUEST": "0", "AUTO_NEXT_ON_THRESHOLD": "0", "AUTO_RESET_SKIP_ENABLED": "0",
    })
    sys.path.insert(0, REPO)
    import live_widget as w
    from werkzeug.serving import make_server
    now = time.time()
    with w.state_lock:
        w.song_queue.extend([
            {"user": "neon_kat", "song": "Blinding Lights by The Weeknd", "ts": now, "request_key": "a",
             "spotify_track": "Blinding Lights", "spotify_artist": "The Weeknd", "duration_sec": 200, "album_art": ART},
            {"user": "dj_marcus", "song": "Levitating by Dua Lipa", "ts": now, "request_key": "b",
             "spotify_track": "Levitating", "spotify_artist": "Dua Lipa", "duration_sec": 203, "album_art": ART},
            {"user": "tomtom", "song": "Heat Waves - Glass Animals", "ts": now, "request_key": "d"},
        ])
        w.now_playing_state.update({"title": "Starboy", "artist": "The Weeknd, Daft Punk", "elapsed": 95,
                                    "duration": 230, "playing": True, "available": True, "album_art": ART})
        w.skip_votes.update({"skips": 3, "threshold": 8, "skippers": ["neon_kat", "tomtom", "lu"], "reached": False,
                             "mode": "adaptive"})
        w.spotify_queue_state.extend([
            {"song": "Blinding Lights", "spotify_track": "Blinding Lights", "spotify_artist": "The Weeknd",
             "spotify_uri": "spotify:track:1", "duration_sec": 200, "album_art": ART, "source": "spotify_queue", "user": "neon_kat"},
            {"song": "Levitating", "spotify_track": "Levitating", "spotify_artist": "Dua Lipa",
             "spotify_uri": "spotify:track:2", "duration_sec": 203, "album_art": ART, "source": "spotify_queue", "user": "dj_marcus"},
        ])
        w.spotify_queue_status.update({"auth_ready": True, "count": 2, "last_error": "", "manual_only": True,
                                       "manual_pending": 2, "manual_mode": "tracked"})
    server = make_server("127.0.0.1", port, w.app, threaded=True)
    print(f"READY http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


def start_server(port):
    proc = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--serve", str(port)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=REPO)
    deadline = time.time() + 40
    while time.time() < deadline:
        line = proc.stdout.readline()
        if line.startswith("READY"):
            return proc, f"http://127.0.0.1:{port}"
        if proc.poll() is not None:
            break
    proc.kill()
    raise SystemExit("Seeded test server failed to start")


# ----------------------------------------------------------------------------- minimal WebSocket + CDP
class WebSocket:
    def __init__(self, url):
        rest = url.split("://", 1)[1]
        hostport, path = rest.split("/", 1)
        host, port = hostport.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=30)
        key = base64.b64encode(secrets.token_bytes(16)).decode()
        self.sock.sendall((f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
                           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        header = b""
        while b"\r\n\r\n" not in header:
            header += self.sock.recv(1)
        if b" 101 " not in header.split(b"\r\n")[0]:
            raise RuntimeError("WebSocket handshake failed: " + header.decode(errors="ignore"))

    def _read(self, n):
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("WebSocket closed")
            data += chunk
        return data

    def send(self, text):
        payload = text.encode()
        header = bytearray([0x81])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", length)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", length)
        mask = secrets.token_bytes(4)
        header += mask
        self.sock.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def recv(self):
        message = b""
        while True:
            first, second = self._read(2)
            opcode = first & 0x0F
            length = second & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read(8))[0]
            if second & 0x80:
                mask = self._read(4)
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(self._read(length)))
            else:
                payload = self._read(length)
            if opcode == 0x8:
                raise ConnectionError("WebSocket closed by peer")
            if opcode == 0x9:
                continue
            message += payload
            if first & 0x80:
                return message.decode()


class Edge:
    """One headless Edge process; each Page is a CDP target attached with flatten sessions."""

    def __init__(self, debug_port):
        self.profile = tempfile.mkdtemp(prefix="edge-check-")
        self.proc = subprocess.Popen([
            find_edge(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
            f"--remote-debugging-port={debug_port}", f"--user-data-dir={self.profile}",
            "--window-size=1280,900", "about:blank",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 30
        while True:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{debug_port}/json/version", timeout=2) as resp:
                    ws_url = json.load(resp)["webSocketDebuggerUrl"]
                break
            except Exception:
                if time.time() > deadline:
                    self.proc.kill()
                    raise SystemExit("Edge did not expose a DevTools endpoint")
                time.sleep(0.3)
        self.ws = WebSocket(ws_url)
        self.next_id = 1
        self.events = []

    def call(self, method, params=None, session=None):
        msg_id = self.next_id
        self.next_id += 1
        payload = {"id": msg_id, "method": method, "params": params or {}}
        if session:
            payload["sessionId"] = session
        self.ws.send(json.dumps(payload))
        while True:
            reply = json.loads(self.ws.recv())
            if reply.get("id") == msg_id:
                if "error" in reply:
                    raise RuntimeError(f"{method}: {reply['error']}")
                return reply.get("result", {})
            self.events.append(reply)

    def new_page(self):
        target = self.call("Target.createTarget", {"url": "about:blank"})["targetId"]
        session = self.call("Target.attachToTarget", {"targetId": target, "flatten": True})["sessionId"]
        self.call("Page.enable", session=session)
        self.call("Runtime.enable", session=session)
        return Page(self, session)

    def close(self):
        try:
            self.call("Browser.close")
        except Exception:
            pass
        self.proc.kill()


class Page:
    def __init__(self, edge, session):
        self.edge = edge
        self.session = session
        self.set_viewport(375, 812)

    def evaluate(self, expression):
        result = self.edge.call("Runtime.evaluate", {
            "expression": expression, "returnByValue": True, "awaitPromise": True
        }, session=self.session)
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"].get("text", "") + " " +
                               json.dumps(result["exceptionDetails"].get("exception", {}))[:500])
        return result.get("result", {}).get("value")

    def goto(self, url):
        self.edge.call("Page.navigate", {"url": url}, session=self.session)
        self.wait_for("document.readyState === 'complete'")
        self.wait_for("typeof socket !== 'undefined' && socket.connected", timeout=20)

    def wait_for(self, expression, timeout=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if self.evaluate(expression):
                    return
            except RuntimeError:
                pass
            time.sleep(0.15)
        raise AssertionError(f"Timed out waiting for: {expression}")

    def set_viewport(self, width, height):
        self.edge.call("Emulation.setDeviceMetricsOverride", {
            "width": width, "height": height, "deviceScaleFactor": 1, "mobile": False
        }, session=self.session)
        self.width, self.height = width, height

    def screenshot(self, path, omit_background=False):
        if omit_background:
            self.edge.call("Emulation.setDefaultBackgroundColorOverride",
                           {"color": {"r": 0, "g": 0, "b": 0, "a": 0}}, session=self.session)
        data = self.edge.call("Page.captureScreenshot", {"format": "png"}, session=self.session)["data"]
        if omit_background:
            self.edge.call("Emulation.setDefaultBackgroundColorOverride", {}, session=self.session)
        if path:
            with open(path, "wb") as handle:
                handle.write(base64.b64decode(data))
        return data

    def style(self, selector, prop):
        return self.evaluate(f"getComputedStyle(document.querySelector({selector!r})).{prop}")

    def visible(self, selector):
        return self.evaluate(
            f"(() => {{ const el = document.querySelector({selector!r}); if (!el) return false;"
            f" const cs = getComputedStyle(el); const r = el.getBoundingClientRect();"
            f" return cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 0 && r.height > 0; }})()")

    def bounds(self, selector):
        return self.evaluate(
            f"(() => {{ const r = document.querySelector({selector!r}).getBoundingClientRect();"
            f" return {{x: r.x, y: r.y, width: r.width, height: r.height}}; }})()")


# ----------------------------------------------------------------------------- checks
class Checker:
    def __init__(self):
        self.failures = []

    def check(self, condition, message):
        status = "ok  " if condition else "FAIL"
        print(f"  [{status}] {message}")
        if not condition:
            self.failures.append(message)


def check_skip_overlay(edge, url, checker, shots):
    print("Skip overlay (/)")
    page = edge.new_page()
    page.goto(url + "/")
    for selector in (".mod-bar", ".test-bar", "#control-auth"):
        checker.check(not page.visible(selector), f"{selector} hidden on overlay")
    checker.check(page.evaluate("!!document.querySelector('.requests-panel.hidden-panel')"), "requests panel hidden by default")
    for selector in ("html", "body", "#voting-panel"):
        checker.check(page.style(selector, "backgroundColor") == "rgba(0, 0, 0, 0)", f"{selector} transparent")
    checker.check(page.style("#voting-panel", "boxShadow") == "none", "#voting-panel has no shadow")
    checker.check(page.style("#voting-panel", "backdropFilter") == "none", "#voting-panel has no backdrop filter")
    checker.check(not page.visible("#voting-panel .border-glow"), "border glow hidden")
    checker.check(not page.visible("#voting-panel .glow-line"), "glow line hidden")
    checker.check(not page.visible("#particles"), "particles hidden")
    checker.check(page.style("#skip-count", "textShadow") != "none", "#skip-count has a text shadow")
    for width, height in ((200, 200), (320, 240), (1920, 1080)):
        page.set_viewport(width, height)
        panel = page.bounds("#voting-panel")
        for selector in (".skip-command-hint", "#skip-meter-circle", "#skip-count"):
            b = page.bounds(selector)
            inside_panel = b["x"] >= panel["x"] - 0.5 and b["x"] + b["width"] <= panel["x"] + panel["width"] + 1
            inside_view = b["y"] >= 0 and b["y"] + b["height"] <= height
            checker.check(b["width"] > 0 and b["height"] > 0 and inside_panel and inside_view,
                          f"{selector} fits the panel and a {width}x{height} source")
    page.set_viewport(200, 200)
    page.wait_for("getComputedStyle(document.getElementById('conn-banner')).opacity === '0'", timeout=8)
    png = page.screenshot(os.path.join(shots, "skip-transparent-200.png") if shots else None, omit_background=True)
    alphas = page.evaluate("""(async (encoded) => {
        const img = new Image(); img.src = 'data:image/png;base64,' + encoded; await img.decode();
        const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
        const g = c.getContext('2d'); g.drawImage(img, 0, 0);
        const p = document.getElementById('voting-panel').getBoundingClientRect();
        return [g.getImageData(0, 0, 1, 1).data[3], g.getImageData(100, 190, 1, 1).data[3],
                g.getImageData(Math.floor(p.x + 2), Math.floor(p.y + p.height / 2), 1, 1).data[3]];
    })(%s)""" % json.dumps(png))
    checker.check(alphas == [0, 0, 0], f"transparent pixels at corner, bottom-center, panel edge: {alphas}")
    if shots:
        page.set_viewport(420, 760)
        page.goto(url + "/?bg=black")
        page.screenshot(os.path.join(shots, "skip-black-420x760.png"))
    page.goto(url + "/?bg=black")
    checker.check(page.style("body", "backgroundColor") == "rgb(0, 0, 0)", "?bg=black paints body black")
    checker.check(page.style("#voting-panel", "backgroundColor") != "rgba(0, 0, 0, 0)", "?bg=black paints the skip panel")
    return page


def check_queue_widget(edge, url, checker, shots):
    print("Queue widget (/queue_widget)")
    page = edge.new_page()
    page.set_viewport(520, 860)
    page.goto(url + "/queue_widget")
    if shots:
        page.screenshot(os.path.join(shots, "queue-520x860.png"))
        page.set_viewport(1280, 720)
        page.wait_for("true")
        page.screenshot(os.path.join(shots, "queue-1280x720.png"))
        page.set_viewport(520, 860)
    page.evaluate("requestQueueItems = [{user: 'Viewer', song: 'First Request by Artist'}];"
                  "spotifyQueueStatus = {auth_ready: false}; syncQueueSourceAndRender(); true")
    checker.check("First Request" in page.evaluate("document.getElementById('queue-list').textContent"),
                  "request queue renders when Spotify is not configured")
    page.evaluate("spotifyQueueStatus = {auth_ready: true, last_error: 'test error'}; spotifyQueueItems = [];"
                  "syncQueueSourceAndRender(); true")
    checker.check("No queued songs" in page.evaluate("document.getElementById('queue-list').textContent"),
                  "empty Spotify queue shows the empty state")
    checker.check("sync unavailable" in page.evaluate("document.getElementById('queue-status').textContent"),
                  "sync error is reported in #queue-status")
    elapsed = page.evaluate("""(() => {
        handleNow({available: true, title: 'Test Song', artist: 'Artist', elapsed: 30, duration: 200, playing: false});
        nowAnchorMs = Date.now() - 90000;
        handleNow({available: true, title: 'Test Song', artist: 'Artist', elapsed: 30, duration: 200, playing: true});
        return currentElapsedSec();
    })()""")
    checker.check(30 <= elapsed < 32, f"playback resumes without jumping ahead (elapsed={elapsed})")
    return page


def check_control_panel(edge, url, checker, shots):
    print("Control panel (/control)")
    page = edge.new_page()
    page.set_viewport(1200, 1400)
    page.goto(url + "/control")
    checker.check(page.style("body", "backgroundColor") == "rgb(0, 0, 0)", "control body is black")
    checker.check(page.style("#voting-panel", "backgroundColor") != "rgba(0, 0, 0, 0)", "control skip panel is opaque")
    checker.check(page.visible("#mod-password"), "password field visible")
    checker.check(page.visible(".control-heading"), "control heading visible")
    page.evaluate("document.getElementById('mod-toggle').click(); true")
    checker.check(not page.visible("#mod-panel"), "moderator panel stays closed while locked")
    page.evaluate("document.getElementById('test-toggle').click();"
                  "document.getElementById('test-message').value = '!req Offline Test by Artist';"
                  "document.getElementById('test-send').click(); true")
    page.wait_for("document.getElementById('control-auth-status').textContent.includes('Enter your control password')")
    checker.check(page.evaluate("document.activeElement.id") == "mod-password", "locked send focuses the password field")
    page.evaluate("document.getElementById('mod-password').value = 'wrong-password';"
                  "document.getElementById('mod-login').click(); true")
    page.wait_for("document.getElementById('control-auth-status').textContent.includes('Password not accepted')")
    page.evaluate(f"document.getElementById('mod-password').value = {PASSWORD!r};"
                  "document.getElementById('mod-login').click(); true")
    page.wait_for("document.getElementById('mod-feedback').textContent.includes('unlocked')")
    page.evaluate("document.getElementById('test-send').click(); true")
    page.wait_for("document.getElementById('test-message').value === ''")
    page.wait_for("document.getElementById('request-count').textContent === '4'")
    checker.check(True, "simulated request reached the queue preview")
    if shots:
        page.screenshot(os.path.join(shots, "control-1200.png"))
        page.set_viewport(390, 1600)
        page.wait_for("true")
        page.screenshot(os.path.join(shots, "control-390.png"))
    return page


def check_no_overflow(pages, checker):
    print("Horizontal overflow")
    for name, page in pages.items():
        for width in (320, 375, 768):
            page.set_viewport(width, 812)
            ok = page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            checker.check(ok, f"{name}: no horizontal overflow at {width}px")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", type=int)
    parser.add_argument("--port", type=int, default=5077)
    parser.add_argument("--debug-port", type=int, default=9333)
    parser.add_argument("--screenshots")
    args = parser.parse_args()
    if args.serve:
        serve(args.serve)
        return
    if args.screenshots:
        os.makedirs(args.screenshots, exist_ok=True)
    server, url = start_server(args.port)
    edge = None
    checker = Checker()
    try:
        edge = Edge(args.debug_port)
        pages = {
            "skip": check_skip_overlay(edge, url, checker, args.screenshots),
            "queue": check_queue_widget(edge, url, checker, args.screenshots),
            "control": check_control_panel(edge, url, checker, args.screenshots),
        }
        check_no_overflow(pages, checker)
    finally:
        if edge:
            edge.close()
        server.kill()
    if checker.failures:
        print(f"\nFAILED: {len(checker.failures)} check(s)")
        for failure in checker.failures:
            print("  - " + failure)
        sys.exit(1)
    print("\nPASS: all Edge overlay checks")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the harness against the current pages**

Run: `.venv/Scripts/python.exe tests/edge_overlay_check.py --screenshots C:\Users\t3076442\AppData\Local\Temp\lw_preview\before`
Expected: `PASS: all Edge overlay checks` (the current markup satisfies the contracts; this proves the harness works before the redesign). If a check fails, fix the harness, not the pages.

- [ ] **Step 3: Document the command**

In `README.md` under "## Test", after the Playwright block, add:

```markdown
Without Node, run the same overlay checks through headless Microsoft Edge:

```powershell
python tests/edge_overlay_check.py --screenshots .\overlay-screenshots
```
```

- [ ] **Step 4: Tick this task's boxes (no git available)**

---

### Task 2: Queue widget redesign

**Files:**
- Modify: `queue_widget.html` (the `<style>` block lines 10–327, markup lines 329–362, `renderNow()` around lines 859–901, `renderQueue()` list rows around lines 757–848, status writing in `renderQueue()` around lines 720–743)
- Test: `tests/edge_overlay_check.py` (add assertions in `check_queue_widget`)

**Interfaces:**
- Produces: new element `#now-artist`; `#queue-status[data-level="info"|"warn"]`; function `applyAccentFromArt(url)` setting `--accent` and `--art-url` on `.widget`; `.now-backdrop` element.
- Consumes: harness `Page` API from Task 1.

- [ ] **Step 1: Add failing harness assertions**

In `check_queue_widget`, after `page.goto(...)`, insert:

```python
    checker.check(page.visible("#now-artist"), "hero shows a separate artist line")
    checker.check(page.evaluate("document.getElementById('now-track').textContent.trim()") == "Starboy",
                  "hero title holds only the title")
    checker.check(page.evaluate("document.getElementById('queue-status').getAttribute('data-level')") == "info",
                  "informational status is tagged info")
    checker.check(not page.visible("#queue-status"), "informational status is hidden from viewers")
    checker.check(page.evaluate("document.querySelectorAll('#queue-list .queue-item .art img').length") == 2,
                  "rows with art render thumbnails")
    checker.check(page.evaluate("getComputedStyle(document.querySelector('.panel.now')).backdropFilter") != "none",
                  "hero uses a glass backdrop")
```
And after the sync-error evaluate, add:
```python
    checker.check(page.evaluate("document.getElementById('queue-status').getAttribute('data-level')") == "warn",
                  "problem status is tagged warn")
    checker.check(page.visible("#queue-status"), "problem status is shown")
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python.exe tests/edge_overlay_check.py`
Expected: FAIL on "hero shows a separate artist line" and the status-level checks.

- [ ] **Step 3: Replace the `<link>` and `<style>` block**

Font link:
```html
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700;800&family=Inter:wght@500;600&display=swap" rel="stylesheet">
```

New stylesheet (replace everything inside `<style>…</style>`):
```css
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
    --accent: #8b7cff;
    --accent-soft: color-mix(in srgb, var(--accent) 35%, transparent);
    --glass: rgba(12, 14, 18, 0.72);
    --glass-opaque: rgba(12, 14, 18, 0.92);
    --line: rgba(255, 255, 255, 0.10);
    --text: #ffffff;
    --text-2: rgba(255, 255, 255, 0.72);
    --text-3: rgba(255, 255, 255, 0.50);
    --radius: 20px;
    --shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
    --font-display: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
    --font-body: 'Inter', system-ui, sans-serif;
    --over-video-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
}
html, body {
    width: 100%; height: 100%; overflow: hidden;
    background: #000; color: var(--text);
    font-family: var(--font-body); font-weight: 500; line-height: 1.3;
    -webkit-font-smoothing: antialiased;
}
html.transparent-bg, html.transparent-bg body { background: transparent; }

.widget { width: 100%; height: 100%; padding: 12px; display: flex; flex-direction: column; gap: 10px; }
.panel {
    position: relative; overflow: hidden; isolation: isolate;
    background: var(--glass); border: 1px solid var(--line); border-radius: var(--radius);
    box-shadow: var(--shadow); backdrop-filter: blur(18px) saturate(140%); -webkit-backdrop-filter: blur(18px) saturate(140%);
}

/* Now playing hero */
.now { padding: 16px; }
.now-backdrop {
    position: absolute; inset: -20%; z-index: -1; pointer-events: none;
    background: var(--art-url, linear-gradient(135deg, #1b1830, #0d1a1f)) center / cover no-repeat;
    filter: blur(40px) brightness(0.55) saturate(1.3); transform: scale(1.3); opacity: 0.65;
    transition: opacity 0.6s ease;
}
.now-wrap { display: flex; gap: 16px; align-items: center; }
.now-art {
    width: clamp(88px, 22vw, 150px); height: clamp(88px, 22vw, 150px); flex-shrink: 0;
    border-radius: 14px; object-fit: cover; background: rgba(255,255,255,0.06);
    box-shadow: 0 8px 24px rgba(0,0,0,0.45);
}
.now-art.no-art { object-fit: contain; padding: 10px; }
.now-main { flex: 1; min-width: 0; }
.eyebrow {
    display: inline-flex; align-items: center; gap: 8px;
    font-size: clamp(11px, 1.6vw, 13px); font-weight: 600; letter-spacing: 0.4px; color: var(--text-2);
}
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 10px var(--accent); animation: breathe 2.4s ease-in-out infinite; }
.paused .live-dot { animation: none; opacity: 0.5; box-shadow: none; }
@keyframes breathe { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(0.75); opacity: 0.55; } }
.track {
    margin-top: 6px; font-family: var(--font-display); font-weight: 800;
    font-size: clamp(20px, 4.4vw, 30px); line-height: 1.15; letter-spacing: -0.3px;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    text-shadow: var(--over-video-shadow);
}
.artist { margin-top: 4px; font-size: clamp(14px, 2.4vw, 17px); font-weight: 600; color: var(--text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.time-row {
    margin-top: 10px; display: flex; align-items: center; justify-content: space-between; gap: 10px;
    font-family: var(--font-display); font-variant-numeric: tabular-nums; font-weight: 700;
    font-size: clamp(12px, 2vw, 14px); color: var(--text-2);
}
.bar { margin-top: 8px; height: 4px; border-radius: 4px; background: rgba(255,255,255,0.14); overflow: hidden; }
.bar-fill { height: 100%; width: 0%; border-radius: 4px; background: var(--accent); box-shadow: 0 0 12px var(--accent-soft); transition: width 0.35s linear; }

/* Up next */
.queue-panel { flex: 1; min-height: 0; padding: 14px 14px 12px; display: flex; flex-direction: column; }
.queue-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.title { font-family: var(--font-display); font-weight: 800; font-size: clamp(16px, 3vw, 20px); letter-spacing: -0.2px; }
.count {
    font-family: var(--font-display); font-weight: 700; font-variant-numeric: tabular-nums;
    font-size: clamp(12px, 1.8vw, 14px); color: var(--text);
    padding: 4px 10px; border-radius: 999px; background: var(--accent-soft); border: 1px solid var(--line);
}
.status {
    margin-bottom: 8px; padding: 6px 10px; border-radius: 10px;
    font-size: clamp(11px, 1.6vw, 13px); font-weight: 600; line-height: 1.3;
    background: rgba(255, 170, 80, 0.14); border: 1px solid rgba(255, 170, 80, 0.35); color: #ffd9a8;
}
.status[data-level="info"] { display: none; }
.queue-list { flex: 1; min-height: 0; overflow-y: auto; scrollbar-width: none; }
.queue-list::-webkit-scrollbar { display: none; }
.queue-item {
    display: grid; grid-template-columns: auto auto minmax(0, 1fr) auto; align-items: center; gap: 12px;
    padding: 10px 12px; margin-bottom: 8px; border-radius: 14px;
    background: rgba(255,255,255,0.05); border: 1px solid var(--line);
    animation: rowIn 0.25s ease-out both;
}
@keyframes rowIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
.pos { font-family: var(--font-display); font-weight: 700; font-variant-numeric: tabular-nums; font-size: clamp(12px, 1.8vw, 14px); color: var(--text-3); min-width: 1.4em; text-align: center; }
.art { width: clamp(44px, 10vw, 56px); height: clamp(44px, 10vw, 56px); border-radius: 10px; overflow: hidden; background: rgba(255,255,255,0.06); flex-shrink: 0; }
.art img { width: 100%; height: 100%; object-fit: cover; display: block; }
.art:empty { display: none; }
.item-main { min-width: 0; }
.song { font-family: var(--font-display); font-weight: 700; font-size: clamp(15px, 2.6vw, 17px); line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-shadow: var(--over-video-shadow); }
.meta { margin-top: 3px; font-size: clamp(12px, 1.9vw, 13px); font-weight: 500; color: var(--text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.meta .sep { margin: 0 6px; color: var(--text-3); }
.eta { text-align: right; font-family: var(--font-display); font-variant-numeric: tabular-nums; }
.eta-start { display: block; font-weight: 700; font-size: clamp(14px, 2.2vw, 16px); white-space: nowrap; }
.eta-end { display: block; margin-top: 2px; font-weight: 600; font-size: clamp(11px, 1.6vw, 12px); color: var(--text-3); white-space: nowrap; }
.eta-label { display: none; }
.empty { height: 100%; display: grid; place-items: center; text-align: center; padding: 20px; color: var(--text-2); font-weight: 600; font-size: clamp(14px, 2.4vw, 17px); line-height: 1.45; }
.empty strong { color: var(--text); font-family: var(--font-display); }

/* Footer hint + toast + connection */
.request-hint {
    margin-top: 10px; padding: 9px 12px; border-radius: 12px; text-align: center;
    background: rgba(255,255,255,0.05); border: 1px solid var(--line);
    font-size: clamp(12px, 1.9vw, 14px); color: var(--text-2); line-height: 1.4;
}
.request-hint strong { color: var(--text); font-family: var(--font-display); font-weight: 700; }
.connection-status { padding: 8px 12px; border-radius: 12px; background: rgba(255, 170, 80, 0.14); border: 1px solid rgba(255, 170, 80, 0.35); color: #ffd9a8; font-size: 13px; font-weight: 600; }
.connection-status[hidden] { display: none; }
.request-toast {
    position: fixed; top: 14px; left: 50%; transform: translateX(-50%) translateY(-22px);
    display: inline-flex; align-items: center; gap: 8px; padding: 9px 14px; border-radius: 999px;
    background: var(--glass-opaque); border: 1px solid var(--line); box-shadow: var(--shadow);
    color: var(--text); font-family: var(--font-display); font-weight: 700; font-size: clamp(12px, 1.8vw, 15px);
    max-width: min(92vw, 900px); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    opacity: 0; pointer-events: none; z-index: 999; transition: opacity 0.25s ease, transform 0.25s ease;
}
.request-toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
.request-toast.accepted { border-color: var(--accent); }
.request-toast.rejected { border-color: rgba(255, 170, 80, 0.7); }
.request-toast-text { overflow: hidden; text-overflow: ellipsis; }

/* Adaptive */
@media (orientation: portrait) {
    .widget { padding: 10px; gap: 8px; }
    .queue-item { padding: 9px 10px; }
}
@media (min-aspect-ratio: 4/3) and (min-width: 640px) {
    .widget { flex-direction: row; align-items: stretch; }
    .now { flex: 0 0 40%; display: flex; }
    .now-wrap { flex-direction: column; align-items: flex-start; width: 100%; }
    .now-art { width: min(100%, 220px); height: auto; aspect-ratio: 1; }
    .now-main { width: 100%; }
    .queue-panel { flex: 1; }
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
}
```

- [ ] **Step 4: Update the markup**

Replace the body markup from `<div class="widget">` through the toast with:
```html
<div class="widget" id="widget">
    <div class="connection-status" id="connection-status" role="status" aria-live="polite">Connecting to overlay server...</div>
    <section class="panel now" id="now-panel" aria-label="Now playing">
        <div class="now-backdrop" aria-hidden="true"></div>
        <div class="now-wrap">
            <img class="now-art no-art" id="now-art" alt="">
            <div class="now-main">
                <div class="eyebrow"><span class="live-dot" aria-hidden="true"></span><span>Now playing</span></div>
                <div class="track" id="now-track">Waiting for Spotify</div>
                <div class="artist" id="now-artist"></div>
                <div class="time-row">
                    <div id="now-time">--:-- / --:--</div>
                    <div id="now-state">-</div>
                </div>
                <div class="bar"><div class="bar-fill" id="now-bar"></div></div>
            </div>
        </div>
    </section>

    <section class="panel queue-panel" aria-label="Up next">
        <div class="queue-head">
            <div class="title">Up Next</div>
            <div class="count" id="queue-count">0 queued</div>
        </div>
        <div class="status" id="queue-status" role="status" aria-live="polite" data-level="info">Waiting for queue sync...</div>
        <div class="queue-list" id="queue-list" role="list" aria-label="Upcoming songs">
            <div class="empty">No queued songs yet</div>
        </div>
        <div class="request-hint">Request: <strong>!req Song by Artist</strong> · Skip: <strong>!skip</strong></div>
    </section>
</div>
<div class="request-toast" id="request-toast" role="status" aria-live="polite">
    <span class="request-toast-icon" id="request-toast-icon">&#127911;</span>
    <span class="request-toast-text" id="request-toast-text"></span>
</div>
```

- [ ] **Step 5: Update the script**

a) After `cacheElements()` definition add `nowArtistEl = document.getElementById('now-artist'); nowPanelEl = document.getElementById('now-panel');` (declare `let nowArtistEl, nowPanelEl;` next to the other cached elements).

b) Accent sampling helper (place after `cacheElements`):
```js
const accentCache = {};
function applyAccentFromArt(url) {
    const root = document.getElementById('widget');
    if (!root) return;
    if (!url || url === FALLBACK_NOW_ART) {
        root.style.removeProperty('--art-url');
        root.style.removeProperty('--accent');
        return;
    }
    root.style.setProperty('--art-url', 'url("' + url.replace(/["\\]/g, '') + '")');
    if (accentCache[url]) { root.style.setProperty('--accent', accentCache[url]); return; }
    try {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = function() {
            try {
                const c = document.createElement('canvas'); c.width = 16; c.height = 16;
                const g = c.getContext('2d'); g.drawImage(img, 0, 0, 16, 16);
                const d = g.getImageData(0, 0, 16, 16).data;
                let r = 0, gg = 0, b = 0, n = 0;
                for (let i = 0; i < d.length; i += 4) {
                    const max = Math.max(d[i], d[i+1], d[i+2]), min = Math.min(d[i], d[i+1], d[i+2]);
                    if (max - min < 24) continue;          // skip greys
                    r += d[i]; gg += d[i+1]; b += d[i+2]; n++;
                }
                if (!n) return;
                r /= n; gg /= n; b /= n;
                const lum = (0.2126*r + 0.7152*gg + 0.0722*b) / 255;
                const target = Math.min(0.75, Math.max(0.45, lum));
                const k = target / Math.max(lum, 0.01);
                const clamp = v => Math.max(0, Math.min(255, Math.round(v * k)));
                const color = 'rgb(' + clamp(r) + ',' + clamp(gg) + ',' + clamp(b) + ')';
                accentCache[url] = color;
                root.style.setProperty('--accent', color);
            } catch (e) { /* tainted canvas or decode issue: keep default accent */ }
        };
        img.src = url;
    } catch (e) { /* keep default accent */ }
}
```

c) In `renderNow()`: in the unavailable branch set `nowArtistEl.textContent = '';`, `nowPanelEl.classList.remove('paused');` and call `applyAccentFromArt('')`. In the available branch, keep `label` for change detection but render `nowTrackEl.textContent = title; nowArtistEl.textContent = artist;`, toggle `nowPanelEl.classList.toggle('paused', !nowPlaying.playing)`, and when `art !== lastArt` call `applyAccentFromArt(art)`.

d) In `renderQueue()` status block: compute `level = 'warn'` for the connection-lost, sync-unavailable, and not-configured branches, else `'info'`; set `status.setAttribute('data-level', level)` alongside `status.textContent`.

e) In the row builder: replace the `artDiv`/`mainDiv`/`etaDiv` construction with:
```js
const div = document.createElement('div'); div.className = 'queue-item'; div.setAttribute('role', 'listitem');
const pos = document.createElement('div'); pos.className = 'pos'; pos.textContent = String(i + 1);
const artDiv = document.createElement('div'); artDiv.className = 'art';
if (p.album_art) {
    const img = document.createElement('img'); img.src = p.album_art; img.alt = ''; img.loading = 'lazy';
    img.decoding = 'async'; img.referrerPolicy = 'no-referrer';
    img.addEventListener('error', function() { img.remove(); }, { once: true });
    artDiv.appendChild(img);
}
const mainDiv = document.createElement('div'); mainDiv.className = 'item-main';
const songDiv = document.createElement('div'); songDiv.className = 'song'; songDiv.textContent = p.title || 'Unknown Song';
const metaDiv = document.createElement('div'); metaDiv.className = 'meta';
if (p.artist) metaDiv.appendChild(document.createTextNode(p.artist));
if (requester) {
    if (p.artist) { const sep = document.createElement('span'); sep.className = 'sep'; sep.textContent = '·'; metaDiv.appendChild(sep); }
    metaDiv.appendChild(document.createTextNode('requested by ' + requester));
} else if (!p.artist) {
    metaDiv.textContent = sourceLabel;
}
mainDiv.appendChild(songDiv); mainDiv.appendChild(metaDiv);
const etaDiv = document.createElement('div'); etaDiv.className = 'eta';
const startValue = document.createElement('span'); startValue.className = 'eta-start'; startValue.setAttribute('data-index', String(i)); startValue.textContent = startTxt;
const endValue = document.createElement('span'); endValue.className = 'eta-end'; endValue.setAttribute('data-index', String(i)); endValue.textContent = endTxt;
etaDiv.appendChild(startValue); etaDiv.appendChild(endValue);
div.appendChild(pos); div.appendChild(artDiv); div.appendChild(mainDiv); div.appendChild(etaDiv);
fragment.appendChild(div);
```
and change `fmtEta` usage so `startTxt = 'in ' + fmtEta(...)` and `endTxt = 'ends ' + fmtEta(...)`; update `refreshQueueEtaLabels()` to write the same prefixes.

f) Empty state: `list.innerHTML = '<div class="empty">Nothing queued yet<br><strong>!req Song by Artist</strong> to add one</div>';`

g) `count.textContent = n + ' queued';`

- [ ] **Step 6: Run harness and unit tests**

Run: `.venv/Scripts/python.exe tests/edge_overlay_check.py --screenshots C:\Users\t3076442\AppData\Local\Temp\lw_preview\after`
Expected: PASS. Then `.venv/Scripts/python.exe -m unittest tests.test_live_widget tests.test_request_latency` → OK.
Open `after/queue-520x860.png` and `after/queue-1280x720.png` and confirm the hero, rows, and hint look as designed.

---

### Task 3: Skip overlay redesign (`index.html` overlay mode)

**Files:**
- Modify: `index.html` — first `<style>` (lines 26–848), third `<style>` overrides (862–955), markup of `.widget-wrapper` (976–1081), `renderQueue()` (1425–1500), `createEmptyState()` (1502–1510), `spawnNotes`/`spawnSkipFloat`/`spawnSkipBurst` (1379–1541), `createParticles` (1164–1178).
- Test: `tests/edge_overlay_check.py` (add assertions in `check_skip_overlay`)

**Interfaces:**
- Produces: unchanged ids; `.request-item .art` only when `item.album_art`; `.request-item .meta` line.
- Consumes: harness Page API.

- [ ] **Step 1: Add failing harness assertions**

In `check_skip_overlay` after the transparency checks:
```python
    checker.check(page.evaluate("document.querySelectorAll('.bg-particles .particle').length") == 0, "no particle nodes are created")
    checker.check(page.evaluate("!document.querySelector('.request-cta-pill')"), "CTA pill removed")
    checker.check(page.evaluate("!document.querySelector('.panel-footer')"), "panel footers removed")
    checker.check(page.evaluate("getComputedStyle(document.querySelector('.skip-count')).fontFamily").startswith('"Plus Jakarta Sans"'), "count uses the display font")
```
And in `check_control_panel` after the request send (where the preview queue is visible and opaque):
```python
    checker.check(page.evaluate("document.querySelectorAll('.request-item .art img').length") == 2, "request rows show art when available")
    checker.check(page.evaluate("document.querySelectorAll('.request-item:not(:has(.art img))').length") >= 1, "art-less rows render without an img")
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python.exe tests/edge_overlay_check.py`
Expected: FAIL on "no particle nodes", "CTA pill removed", "panel footers removed".

- [ ] **Step 3: Rewrite the first `<style>` block**

Keep the same selectors that JS toggles (`.newest`, `.flash`, `.danger`, `.full`, `.active`, `.glowing`, `.bump`, `.threshold-flash`, `.scrolling`, `.hidden-panel`, `.show`, `.compact-skip`, `.controls-mode`, `.transparent-bg`). Tokens identical to Task 2 `:root`. Key components:

```css
.panel-card { position: relative; display: flex; flex-direction: column; overflow: hidden; isolation: isolate;
    background: var(--glass-opaque); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); }
.border-glow, .glow-line, .panel-footer, .bg-particles { display: none; }
.panel-inner { position: relative; z-index: 1; display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.panel-header { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 14px 14px 8px; flex-shrink: 0; }
.panel-title { font-family: var(--font-display); font-weight: 800; font-size: clamp(16px, 3vw, 20px); letter-spacing: -0.2px; color: var(--text); }
.panel-subtitle { font-size: clamp(12px, 1.8vw, 13px); color: var(--text-2); font-weight: 500; }
.header-badges { display: flex; gap: 6px; }
.badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; background: var(--accent-soft); border: 1px solid var(--line);
    font-family: var(--font-display); font-weight: 700; font-variant-numeric: tabular-nums; font-size: clamp(12px, 1.8vw, 14px); }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 10px var(--accent); animation: breathe 2.4s ease-in-out infinite; }

.request-list { flex: 1; min-height: 0; overflow-y: auto; padding: 4px 12px 12px; scrollbar-width: none; }
.request-list::-webkit-scrollbar { display: none; }
.request-item { display: grid; grid-template-columns: auto auto minmax(0,1fr) auto; align-items: center; gap: 12px; padding: 10px 12px; margin-bottom: 8px;
    border-radius: 14px; background: rgba(255,255,255,0.05); border: 1px solid var(--line); animation: rowIn 0.25s ease-out both; }
.request-item.newest { border-color: var(--accent); }
.request-item.flash { animation: rowIn 0.25s ease-out both, flashIn 0.9s ease-out; }
@keyframes flashIn { 0% { background: var(--accent-soft); } 100% { background: rgba(255,255,255,0.05); } }
.pos { font-family: var(--font-display); font-weight: 700; font-size: clamp(12px, 1.8vw, 14px); color: var(--text-3); min-width: 1.4em; text-align: center; }
.art { width: clamp(44px, 10vw, 56px); height: clamp(44px, 10vw, 56px); border-radius: 10px; overflow: hidden; background: rgba(255,255,255,0.06); }
.art img { width: 100%; height: 100%; object-fit: cover; display: block; }
.art:empty { display: none; }
.song-details { min-width: 0; }
.song-name { font-family: var(--font-display); font-weight: 700; font-size: clamp(15px, 2.6vw, 17px); line-height: 1.2; overflow: hidden; white-space: nowrap; text-shadow: var(--over-video-shadow); }
.song-name-inner { display: inline-block; white-space: nowrap; }
.song-name-inner.scrolling { animation: marqueeScroll 11s linear 2; padding-right: 30px; }
@keyframes marqueeScroll { 0%, 15% { transform: translateX(0); } 85%, 100% { transform: translateX(calc(-100% + 80px)); } }
.meta { margin-top: 3px; font-size: clamp(12px, 1.9vw, 13px); color: var(--text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.meta .sep { margin: 0 6px; color: var(--text-3); }
.user-tag { display: inline; font-weight: 600; color: var(--text-2); }
.eta-tag { text-align: right; font-family: var(--font-display); font-variant-numeric: tabular-nums; font-weight: 700; font-size: clamp(14px, 2.2vw, 16px); white-space: nowrap; color: var(--text); }
.eta-tag small { display: block; margin-top: 2px; font-size: clamp(11px, 1.6vw, 12px); font-weight: 600; color: var(--text-3); }
.new-badge { display: inline-block; margin-left: 8px; padding: 2px 6px; border-radius: 6px; background: var(--accent); color: #fff; font-size: 10px; font-weight: 800; vertical-align: middle; }
.empty-state { display: grid; place-items: center; text-align: center; padding: 28px 14px; color: var(--text-2); font-weight: 600; line-height: 1.45; }
.empty-state strong { color: var(--text); font-family: var(--font-display); }

/* Skip meter */
.voting-content { padding: 10px 12px 12px; display: flex; flex-direction: column; align-items: center; gap: 8px; }
.skip-meter-circle { position: relative; width: 108px; height: 108px; }
.skip-circle-bg, .skip-circle-fill { position: absolute; inset: 0; width: 100%; height: 100%; }
.skip-circle-bg circle { fill: none; stroke: rgba(255,255,255,0.18); stroke-width: 6; }
.skip-circle-fill { transform: rotate(-90deg); }
.skip-circle-fill circle { fill: none; stroke: var(--accent); stroke-width: 6; stroke-linecap: round; stroke-dasharray: 263.894; stroke-dashoffset: 263.894;
    transition: stroke-dashoffset 0.6s ease-out, stroke 0.4s ease; filter: drop-shadow(0 0 6px var(--accent-soft)); }
.skip-circle-fill.danger circle { stroke: #ff9f43; }
.skip-circle-fill.full circle { stroke: #ff5c5c; animation: ringPulse 1s ease-in-out infinite; }
@keyframes ringPulse { 0%, 100% { filter: drop-shadow(0 0 4px rgba(255,92,92,0.4)); } 50% { filter: drop-shadow(0 0 14px rgba(255,92,92,0.9)); } }
.skip-meter-center { position: absolute; inset: 0; display: grid; place-content: center; text-align: center; }
.skip-emoji { display: none; }
.skip-count { font-family: var(--font-display); font-weight: 800; font-size: 34px; line-height: 1; color: var(--text); text-shadow: var(--over-video-shadow); }
.skip-count.bump { animation: countBump 0.4s ease-out; }
@keyframes countBump { 0% { transform: scale(1); } 35% { transform: scale(1.25); } 100% { transform: scale(1); } }
.skip-of-text { margin-top: 2px; font-family: var(--font-display); font-weight: 700; font-size: 12px; color: var(--text-2); text-shadow: var(--over-video-shadow); }
.skip-mode-text { display: none; }
.skip-pulse-ring { position: absolute; top: 50%; left: 50%; width: 30px; height: 30px; border: 2px solid var(--accent); border-radius: 50%;
    transform: translate(-50%, -50%) scale(0); opacity: 0; pointer-events: none; }
.skip-pulse-ring.active { animation: ringExpand 0.8s ease-out forwards; }
@keyframes ringExpand { 0% { transform: translate(-50%,-50%) scale(0); opacity: 0.7; } 100% { transform: translate(-50%,-50%) scale(3.4); opacity: 0; } }
.skip-command-hint { display: flex; align-items: baseline; justify-content: center; gap: 6px; }
.skip-command-box { font-family: var(--font-display); font-weight: 800; font-size: clamp(15px, 2.2vw, 18px); color: var(--text); text-shadow: var(--over-video-shadow); }
.skip-command-arrow { display: none; }
.skip-cta-text { font-size: clamp(12px, 1.8vw, 13px); font-weight: 600; color: var(--text-2); text-shadow: var(--over-video-shadow); }
.skip-bar-wrap { width: 100%; height: 4px; border-radius: 4px; background: rgba(255,255,255,0.14); overflow: hidden; }
.skip-bar-fill { height: 100%; width: 0%; background: var(--accent); transition: width 0.6s ease-out; }
.skip-bar-fill.danger { background: #ff9f43; } .skip-bar-fill.full { background: #ff5c5c; }
.skip-bar-labels { display: flex; justify-content: space-between; margin-top: 4px; font-size: 11px; color: var(--text-3); font-weight: 600; }
.recent-skippers { display: flex; gap: 4px; flex-wrap: wrap; justify-content: center; }
.skipper-chip { padding: 3px 8px; border-radius: 999px; background: rgba(255,255,255,0.06); border: 1px solid var(--line); font-size: 11px; font-weight: 600; color: var(--text-2); }
.skipper-icon { display: none; }
.skip-warning { overflow: hidden; max-height: 0; opacity: 0; transition: max-height 0.4s ease, opacity 0.4s ease; }
.skip-warning.active { max-height: 44px; opacity: 1; }
.skip-warning-inner { display: flex; align-items: center; justify-content: center; gap: 6px; padding: 6px 12px; border-radius: 999px; background: rgba(255,92,92,0.18); border: 1px solid rgba(255,92,92,0.5); }
.skip-warning-icon { display: none; }
.skip-warning-text { font-family: var(--font-display); font-weight: 800; font-size: 13px; color: #fff; }
.now-playing-line { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin: 0 14px 6px; padding: 6px 10px; border-radius: 10px; background: rgba(255,255,255,0.05); border: 1px solid var(--line); }
.now-playing-track { flex: 1; min-width: 0; font-size: 12px; font-weight: 600; color: var(--text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.now-playing-time { font-family: var(--font-display); font-variant-numeric: tabular-nums; font-size: 12px; font-weight: 700; color: var(--text-2); }

/* compact meter (default overlay) */
.compact-skip { width: min(170px, 100%); margin: 0 auto; }
.compact-skip .panel-header, .compact-skip .now-playing-line, .compact-skip .header-badges, .compact-skip .skip-bar-wrap,
.compact-skip .skip-bar-labels, .compact-skip .recent-skippers, .compact-skip .skip-warning { display: none; }
.compact-skip .voting-content { padding: 6px 8px 8px; gap: 6px; }
.compact-skip .skip-meter-circle { width: 96px; height: 96px; }
.compact-skip .skip-count { font-size: 30px; }
.compact-skip .skip-of-text { font-size: 11px; }
```
Toasts (`.panel-toast`), `.conn-banner`, `.mod-bar`, `.test-bar` keep their ids; restyle them with glass tokens (background `var(--glass-opaque)`, `border: 1px solid var(--line)`, radius 999px for toasts). Keep the `@media (prefers-reduced-motion: reduce)` block.

Transparent-mode rules (replace the old third `<style>` block's `html.transparent-bg …` section):
```css
html.transparent-bg .bg-particles { display: none; }
html.transparent-bg .widget-wrapper { min-height: 0; padding: 8px; }
html.transparent-bg .voting-panel { background: transparent !important; border: 0; box-shadow: none; backdrop-filter: none; -webkit-backdrop-filter: none; overflow: visible; }
html.transparent-bg .voting-panel .border-glow, html.transparent-bg .voting-panel .glow-line { display: none; }
html.transparent-bg .voting-panel .skip-count, html.transparent-bg .voting-panel .skip-of-text,
html.transparent-bg .voting-panel .skip-command-box, html.transparent-bg .voting-panel .skip-cta-text { text-shadow: 0 1px 2px #000, 0 0 6px rgba(0,0,0,0.9) !important; }
html.transparent-bg .voting-panel .skip-circle-bg circle { stroke: rgba(255,255,255,0.45); }
html.transparent-bg .voting-panel .skip-circle-bg circle, html.transparent-bg .voting-panel .skip-circle-fill circle { filter: drop-shadow(0 1px 2px #000); }
```

- [ ] **Step 4: Update markup**

Requests panel header:
```html
<div class="panel-header">
    <div>
        <h1 class="panel-title">Song Requests</h1>
        <div class="panel-subtitle" role="note">Type !req Song by Artist</div>
    </div>
    <div class="header-badges">
        <div class="badge"><span class="badge-number" id="request-count">0</span> queued</div>
    </div>
</div>
```
Remove `.request-cta-pill`, the "Live" badge, both `.panel-footer` blocks, and the `<div class="bg-particles" id="particles"></div>` stays but empty (CSS hides it; JS no longer populates it — replace the `createParticles` IIFE body with a comment `// Background particles removed for on-stream clarity.`).

Skip panel header: keep structure; remove emoji from `.panel-title` text ("Skip Meter") and the subtitle text becomes "Type !skip to vote". Keep `#now-playing-line`, `#skip-count-badge`. Inside `.skip-command-hint` keep all three spans (arrow hidden via CSS).

- [ ] **Step 5: Update `renderQueue()` rows and effects**

Replace the `div.innerHTML = …` template with:
```js
var artHtml = item.album_art ? '<div class="art"><img alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" src="' + escapeHtml(String(item.album_art)) + '"></div>' : '<div class="art"></div>';
var artistText = escapeHtml(item.spotify_artist || p.artist);
var titleText = escapeHtml(item.spotify_track || p.title);
var metaHtml = (artistText ? artistText + '<span class="sep">·</span>' : '') + '<span class="user-tag">requested by ' + requesterText + '</span>';
div.innerHTML =
    '<div class="pos">' + (i + 1) + '</div>' + artHtml +
    '<div class="song-details">' +
        '<div class="song-name"><span class="song-name-inner">' + titleText + badge + '</span></div>' +
        '<div class="meta">' + metaHtml + '</div>' +
    '</div>' +
    '<div class="eta-tag" data-index="' + i + '">' + (win.estimatedStart ? '~' : '') + 'in ' + formatClock(win.startSec) +
        '<small>' + (win.estimatedEnd ? '~' : '') + 'ends ' + formatClock(win.endSec) + '</small></div>';
```
Update `refreshQueueEtaLabels`-equivalent code (the `.eta-tag[data-index]` refresh at line ~1271) to write the same two-part markup. Make `spawnNotes`, `spawnSkipFloat`, `spawnSkipBurst` bodies `return;` with a comment. `createEmptyState()` returns `<div class="empty-state">Nothing queued yet<br><strong>!req Song by Artist</strong> to add one</div>`.

Remove `.artist-name` usage (folded into `.meta`).

- [ ] **Step 6: Run harness + unit tests, inspect screenshots**

Run: `.venv/Scripts/python.exe tests/edge_overlay_check.py --screenshots C:\Users\t3076442\AppData\Local\Temp\lw_preview\after`
Expected: PASS (including the 200×200 transparency pixel check). Inspect `skip-transparent-200.png` and `skip-black-420x760.png`.

---

### Task 4: Control panel dashboard (`index.html` controls mode)

**Files:**
- Modify: `index.html` — controls-mode CSS (in the third `<style>` block), header/auth/mod/test markup (958–973, 1087–1126), JS: `renderQueue`, `updateSkipMeter`, now-playing render (~1284–1320), socket connect/disconnect handlers (~1629–1700).
- Test: `tests/edge_overlay_check.py` (assertions in `check_control_panel`)

**Interfaces:**
- Produces: `#control-status` strip with `#status-connection`, `#status-now`, `#status-requests`, `#status-skips`; `.control-grid`; `.preview-card`. Helper `setStatusTile(id, text)`.

- [ ] **Step 1: Add failing harness assertions**

In `check_control_panel` after the heading check:
```python
    for tile in ("#status-connection", "#status-now", "#status-requests", "#status-skips"):
        checker.check(page.visible(tile), f"{tile} visible")
    checker.check(page.evaluate("document.getElementById('status-connection').textContent.toLowerCase()").find("connected") >= 0, "connection tile reports connected")
    checker.check(page.evaluate("document.getElementById('status-requests').textContent") == "3", "requests tile shows the queue size")
    checker.check(page.evaluate("document.getElementById('status-skips').textContent") == "3 / 8", "skip tile shows votes / threshold")
    checker.check(page.evaluate("getComputedStyle(document.querySelector('.control-grid')).display") == "grid", "cards laid out as a grid")
```
Also change the later `request-count === '4'` wait to additionally check `status-requests === '4'`.

- [ ] **Step 2: Run to verify failure**

Expected: FAIL on the four tile visibility checks.

- [ ] **Step 3: Markup**

Replace `.control-heading` and `#control-auth` … through the end of `.test-bar` with:
```html
<header class="control-heading">
    <div class="control-title-row">
        <div>
            <h1>Live Widget Controls</h1>
            <p>Keep this page off-stream. <a href="/" target="_blank" rel="noopener">Skip overlay</a> · <a href="/queue_widget" target="_blank" rel="noopener">Song queue overlay</a></p>
        </div>
    </div>
    <div class="control-status" id="control-status" role="status" aria-live="polite">
        <div class="status-tile"><span class="tile-label">Connection</span><span class="tile-value" id="status-connection">Connecting…</span></div>
        <div class="status-tile"><span class="tile-label">Now playing</span><span class="tile-value" id="status-now">Waiting for Spotify</span></div>
        <div class="status-tile"><span class="tile-label">Requests</span><span class="tile-value" id="status-requests">0</span></div>
        <div class="status-tile"><span class="tile-label">Skip votes</span><span class="tile-value" id="status-skips">0 / 0</span></div>
    </div>
</header>
<div class="control-grid">
    <section class="control-card control-auth" id="control-auth" aria-labelledby="control-auth-title"> …existing auth contents unchanged… </section>
    <section class="control-card mod-bar"> …existing mod-toggle + mod-panel unchanged… </section>
    <section class="control-card test-bar"> …existing test-toggle + test-panel unchanged… </section>
</div>
<div class="preview-card">
    <div class="preview-label">Overlay preview · what viewers see</div>
    <div class="widget-wrapper" role="main" aria-label="TikTok Live Widget"> …existing panels… </div>
</div>
```
Note: `.mod-bar` and `.test-bar` move from after `.widget-wrapper` to before it. Overlay mode must still hide them: keep `.mod-bar, .test-bar, .control-heading, .control-auth, .control-grid, .preview-label { display: none; }` and show them only under `.controls-mode`. `.bg-particles` div stays.

- [ ] **Step 4: Controls-mode CSS**

```css
.controls-mode .control-heading { display: block; width: min(100% - 32px, 1200px); margin: 24px auto 0; }
.control-heading h1 { font-family: var(--font-display); font-weight: 800; font-size: 26px; letter-spacing: -0.3px; }
.control-heading p { margin-top: 6px; font-size: 14px; color: var(--text-2); }
.control-heading a { color: var(--accent); }
.controls-mode .control-status { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; margin-top: 16px; }
.status-tile { padding: 12px 14px; border-radius: 14px; background: var(--glass-opaque); border: 1px solid var(--line); min-width: 0; }
.tile-label { display: block; font-size: 12px; font-weight: 600; color: var(--text-3); }
.tile-value { display: block; margin-top: 4px; font-family: var(--font-display); font-weight: 700; font-size: 16px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.controls-mode .control-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; width: min(100% - 32px, 1200px); margin: 16px auto 0; }
.controls-mode .control-card { display: flex; flex-direction: column; gap: 10px; padding: 16px; border-radius: var(--radius); background: var(--glass-opaque); border: 1px solid var(--line); position: static; }
.controls-mode .mod-bar, .controls-mode .test-bar { display: flex; inset: auto; width: auto; margin: 0; }
.controls-mode .mod-panel, .controls-mode .test-panel { width: 100%; padding: 0; margin-top: 4px; background: transparent; border: 0; }
.controls-mode .preview-card { width: min(100% - 32px, 1200px); margin: 16px auto 32px; padding: 16px; border-radius: var(--radius); background: var(--glass-opaque); border: 1px solid var(--line); }
.controls-mode .preview-label { display: block; margin-bottom: 12px; font-size: 13px; font-weight: 600; color: var(--text-2); }
.controls-mode .widget-wrapper { height: auto; min-height: 0; padding: 0; max-width: 560px; margin: 0 auto; }
.controls-mode .requests-panel { flex: none; height: 420px; }
.controls-mode button, .controls-mode input:not([type="checkbox"]), .controls-mode textarea { min-height: 44px; font: inherit; font-size: 14px; border-radius: 10px; border: 1px solid var(--line); background: rgba(255,255,255,0.06); color: var(--text); padding: 8px 12px; }
.controls-mode .mod-toggle, .controls-mode .test-toggle { font-family: var(--font-display); font-weight: 700; text-align: left; }
.controls-mode .mod-btn, .controls-mode .test-send { font-weight: 600; cursor: pointer; }
.controls-mode .mod-btn:hover, .controls-mode .test-send:hover { background: rgba(255,255,255,0.10); }
.controls-mode .test-send { background: var(--accent); border-color: transparent; }
button:focus-visible, input:focus-visible, textarea:focus-visible, a:focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
.controls-mode .conn-banner { top: auto; bottom: 12px; }
```

- [ ] **Step 5: JS status tiles**

Add near the toast helpers:
```js
function setStatusTile(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
}
```
Call sites: in `renderQueue` after updating `request-count`: `setStatusTile('status-requests', String(queueItems.length));`. In `updateSkipMeter` after `ofText.textContent`: `setStatusTile('status-skips', skips + ' / ' + threshold);`. Where `#now-playing-track` is set (both places): `setStatusTile('status-now', label)` using the same text minus the "Now: " prefix. In socket `connect`: `setStatusTile('status-connection', 'Connected')`; in `disconnect`/`connect_error`: `setStatusTile('status-connection', 'Disconnected')`.

- [ ] **Step 6: Run harness + unit tests; inspect `control-1200.png` and `control-390.png`**

Expected: PASS; single-column stacking at 390px; three cards side by side at 1200px.

---

### Task 5: Docs, changelog, final verification

**Files:**
- Modify: `CHANGELOG.md` (Overlay and backend section), `README.md` (nothing beyond Task 1 unless copy changed)

- [ ] **Step 1: Changelog**

Add under "### Overlay and backend":
```markdown
- Redesigned both overlays and the control panel as one "album-art glass" system: frosted cards tinted by the current album art, Plus Jakarta Sans + Inter, calmer motion, album-art thumbnails in every queue row, and a dashboard layout for the control page.
- Added `tests/edge_overlay_check.py`, a headless Microsoft Edge port of the browser overlay checks for machines without Node.
```

- [ ] **Step 2: Full verification**

Run, in order:
1. `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"` → only the 4 known launcher/batch failures remain.
2. `.venv/Scripts/python.exe tests/edge_overlay_check.py --screenshots C:\Users\t3076442\AppData\Local\Temp\lw_preview\final` → PASS.
3. Open every PNG in `final/` and confirm: no clipped text, thumbnails visible, ring fits at 200×200, control cards stack on narrow widths.

- [ ] **Step 3: Report**

List any Playwright assertions the harness could not reproduce (currently: multi-page visibility toggling via `#vis-requests`/`#vis-skip`, offline/reconnect behavior, and CSP console error capture) so the user knows what to run once Node is available.
