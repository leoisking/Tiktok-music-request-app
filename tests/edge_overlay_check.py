"""Headless-Edge checks for the overlay pages when Node/Playwright is unavailable.

Usage:
    python tests/edge_overlay_check.py [--screenshots DIR] [--port 5077] [--debug-port 9333]
    python tests/edge_overlay_check.py --serve 5077   # internal: seeded test server

Drives Microsoft Edge over the Chrome DevTools Protocol with a stdlib-only WebSocket
client and ports the key assertions from tests/test_overlays.cjs.
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
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=REPO,
                            encoding="utf-8", errors="replace")
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
    """One headless Edge process; each Page is a CDP target attached with a flat session."""

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
        return Page(self, session, target)

    def close(self):
        try:
            self.call("Browser.close")
        except Exception:
            pass
        self.proc.kill()


class Page:
    def __init__(self, edge, session, target_id):
        self.edge = edge
        self.session = session
        self.target_id = target_id
        self.set_viewport(375, 812)

    def activate(self):
        """Bring this target to the front; background tabs pause rendering in headless mode."""
        self.edge.call("Target.activateTarget", {"targetId": self.target_id})

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
        # Give layout a moment to settle before callers measure anything (rAF is paused for background tabs).
        self.evaluate("new Promise(r => setTimeout(r, 60))")

    def screenshot(self, path, omit_background=False):
        self.activate()
        self.evaluate("new Promise(r => setTimeout(r, 120))")
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
    checker.check(page.evaluate("document.querySelectorAll('.bg-particles .particle').length") == 0, "no particle nodes are created")
    checker.check(page.evaluate("!document.querySelector('.request-cta-pill')"), "CTA pill removed")
    checker.check(page.evaluate("!document.querySelector('.panel-footer')"), "panel footers removed")
    checker.check(page.evaluate("getComputedStyle(document.querySelector('.skip-count')).fontFamily").startswith('"Plus Jakarta Sans"'),
                  "count uses the display font")
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
    if shots:
        page.screenshot(os.path.join(shots, "queue-520x860.png"))
        page.set_viewport(1280, 720)
        page.screenshot(os.path.join(shots, "queue-1280x720.png"))
        page.set_viewport(520, 860)
    page.evaluate("requestQueueItems = [{user: 'Viewer', song: 'First Request by Artist'}];"
                  "spotifyQueueStatus = {auth_ready: false}; syncQueueSourceAndRender(); true")
    checker.check("First Request" in page.evaluate("document.getElementById('queue-list').textContent"),
                  "request queue renders when Spotify is not configured")
    page.evaluate("spotifyQueueStatus = {auth_ready: true, last_error: 'test error'}; spotifyQueueItems = [];"
                  "syncQueueSourceAndRender(); true")
    checker.check("First Request" in page.evaluate("document.getElementById('queue-list').textContent"),
                  "local request remains visible while Spotify queue is empty")
    checker.check("sync unavailable" in page.evaluate("document.getElementById('queue-status').textContent"),
                  "sync error is reported in #queue-status")
    checker.check(page.evaluate("document.getElementById('queue-status').getAttribute('data-level')") == "warn",
                  "problem status is tagged warn")
    checker.check(page.visible("#queue-status"), "problem status is shown")
    elapsed = page.evaluate("""(() => {
        handleNow({available: true, title: 'Test Song', artist: 'Artist', elapsed: 30, duration: 200, playing: false});
        nowAnchorMs = Date.now() - 90000;
        handleNow({available: true, title: 'Test Song', artist: 'Artist', elapsed: 30, duration: 200, playing: true});
        return currentElapsedSec();
    })()""")
    checker.check(30 <= elapsed < 32, f"playback resumes without jumping ahead (elapsed={elapsed})")
    return page


def check_control_panel(edge, url, checker, shots, overlay):
    print("Control panel (/control)")
    page = edge.new_page()
    page.set_viewport(1200, 1400)
    page.goto(url + "/control")
    checker.check(page.style("body", "backgroundColor") == "rgb(0, 0, 0)", "control body is black")
    checker.check(page.style("#voting-panel", "backgroundColor") != "rgba(0, 0, 0, 0)", "control skip panel is opaque")
    checker.check(page.visible("#mod-password"), "password field visible")
    checker.check(page.visible(".control-heading"), "control heading visible")
    for tile in ("#status-connection", "#status-now", "#status-requests", "#status-skips"):
        checker.check(page.visible(tile), f"{tile} visible")
    checker.check("connected" in page.evaluate("document.getElementById('status-connection').textContent.toLowerCase()"),
                  "connection tile reports connected")
    checker.check(page.evaluate("document.getElementById('status-requests').textContent") == "3", "requests tile shows the queue size")
    checker.check(page.evaluate("document.getElementById('status-skips').textContent") == "3 / 8", "skip tile shows votes / threshold")
    checker.check(page.evaluate("getComputedStyle(document.querySelector('.control-grid')).display") == "grid", "cards laid out as a grid")
    checker.check(page.evaluate("document.querySelectorAll('.request-item .art img').length") == 2, "request rows show art when available")
    checker.check(page.evaluate("document.querySelectorAll('.request-item:not(:has(.art img))').length") >= 1, "art-less rows render without an img")
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
    checker.check(page.evaluate("document.getElementById('status-requests').textContent") == "4", "requests tile follows the queue")
    if shots:
        page.screenshot(os.path.join(shots, "control-1200.png"))
        page.set_viewport(390, 1600)
        page.screenshot(os.path.join(shots, "control-390.png"))
        page.set_viewport(1200, 1400)

    # Visibility toggles reach the overlay page (the same flow the Playwright suite exercises).
    page.evaluate("document.getElementById('mod-toggle').click(); true")
    checker.check(page.visible("#mod-panel"), "moderator panel opens once unlocked")
    page.evaluate("(() => { const c = document.getElementById('vis-requests'); c.checked = true; c.dispatchEvent(new Event('change')); return true; })()")
    overlay.wait_for("!document.querySelector('.requests-panel').classList.contains('hidden-panel')")
    checker.check(True, "requests panel appears on the overlay when enabled")
    overlay.wait_for("document.getElementById('request-count').textContent === '4'")
    checker.check(overlay.evaluate("document.querySelectorAll('.request-item .art img').length") == 2,
                  "overlay request rows show art when available")
    if shots:
        overlay.set_viewport(420, 760)
        overlay.screenshot(os.path.join(shots, "skip-requests-420x760.png"))
    page.evaluate("(() => { const c = document.getElementById('vis-skip'); c.checked = false; c.dispatchEvent(new Event('change')); return true; })()")
    overlay.wait_for("document.querySelector('.voting-panel').classList.contains('hidden-panel')")
    checker.check(True, "skip meter hides on the overlay when disabled")
    page.evaluate("(() => { const c = document.getElementById('vis-skip'); c.checked = true; c.dispatchEvent(new Event('change'));"
                  " const r = document.getElementById('vis-requests'); r.checked = false; r.dispatchEvent(new Event('change')); return true; })()")
    overlay.wait_for("document.querySelector('.requests-panel').classList.contains('hidden-panel')"
                     " && !document.querySelector('.voting-panel').classList.contains('hidden-panel')")
    checker.check(True, "overlay returns to the default layout")
    return page


def check_no_overflow(pages, checker):
    print("Horizontal overflow")
    for name, page in pages.items():
        page.activate()
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
        pages = {}
        pages["skip"] = check_skip_overlay(edge, url, checker, args.screenshots)
        pages["queue"] = check_queue_widget(edge, url, checker, args.screenshots)
        pages["control"] = check_control_panel(edge, url, checker, args.screenshots, pages["skip"])
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
