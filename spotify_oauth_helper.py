import base64
import json
import os
import secrets
import ssl
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer


AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "user-modify-playback-state user-read-playback-state user-read-currently-playing"
CERTIFICATE_HELP = (
    "Could not verify Spotify's HTTPS certificate. A firewall or security product on this network is "
    "intercepting HTTPS traffic. Use a network without inspection (for example your home connection), or set the "
    "SSL_CERT_FILE environment variable to a certificate bundle that includes that product's root certificate."
)


def verifying_ssl_context():
    """Full certificate and hostname verification without Python 3.13+'s strict RFC 5280 extension checks.

    Strict mode rejects otherwise-trusted CA certificates that omit the Authority Key Identifier
    extension, which is common for corporate TLS-inspection firewalls. Browsers accept those chains,
    so the app does too. Verification itself is never disabled.
    """
    context = ssl.create_default_context()
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


def _is_certificate_error(error):
    while error is not None:
        if isinstance(error, ssl.SSLCertVerificationError):
            return True
        if isinstance(error, ssl.SSLError) and "CERTIFICATE_VERIFY_FAILED" in str(error):
            return True
        error = getattr(error, "reason", None) if isinstance(error, urllib.error.URLError) else getattr(error, "__cause__", None)
    return False


def _build_basic_auth(client_id, client_secret):
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _exchange_code_for_tokens(client_id, client_secret, code, redirect_uri):
    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": _build_basic_auth(client_id, client_secret),
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20, context=verifying_ssl_context()) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, ssl.SSLError) as error:
        if _is_certificate_error(error):
            raise RuntimeError(CERTIFICATE_HELP) from error
        raise
    return payload


class CallbackServer:
    def __init__(self, host, port, expected_state, callback_path="/callback"):
        self.host = host
        self.port = port
        self.expected_state = expected_state
        self.callback_path = callback_path
        self.code = None
        self.error = None
        self.done = threading.Event()
        self.httpd = None

    def start(self):
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path != parent.callback_path:
                    self.send_response(404)
                    self.end_headers()
                    return

                try:
                    params = urllib.parse.parse_qs(parsed.query, max_num_fields=10)
                except ValueError:
                    self.send_response(400)
                    self.end_headers()
                    return
                state = (params.get("state") or [""])[0]
                code = (params.get("code") or [""])[0]
                error = (params.get("error") or [""])[0]
                error_description = (params.get("error_description") or [""])[0]

                if not secrets.compare_digest(state.encode("utf-8"), parent.expected_state.encode("utf-8")):
                    self.send_response(400)
                    self.end_headers()
                    return
                if parent.done.is_set():
                    self.send_response(409)
                    self.end_headers()
                    return
                if error:
                    detail = f" ({error_description})" if error_description else ""
                    parent.error = f"Spotify returned error: {error}{detail}"
                elif not code:
                    parent.error = "No authorization code in callback."
                else:
                    parent.code = code

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                if parent.error:
                    self.wfile.write(
                        b"<html><body><h2>Spotify OAuth failed.</h2><p>Go back to terminal for details.</p></body></html>"
                    )
                else:
                    self.wfile.write(
                        b"<html><body><h2>Spotify OAuth complete.</h2><p>You can close this tab and return to terminal.</p></body></html>"
                    )
                parent.done.set()

            def log_message(self, format, *args):
                return

        self.httpd = HTTPServer((self.host, self.port), Handler)
        thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        thread.start()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()


def main():
    client_id = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", DEFAULT_REDIRECT_URI).strip()

    if not client_id or not client_secret:
        print("[ERROR] Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET.")
        print("Set them in this terminal and run again.")
        return 1

    try:
        parsed_redirect = urllib.parse.urlparse(redirect_uri)
        valid_redirect = (
            parsed_redirect.scheme == "http"
            and parsed_redirect.hostname in ("127.0.0.1", "localhost")
            and parsed_redirect.port
            and parsed_redirect.path.startswith("/")
            and not (parsed_redirect.username or parsed_redirect.password or parsed_redirect.query or parsed_redirect.fragment)
        )
    except ValueError:
        valid_redirect = False
    if not valid_redirect:
        print("[ERROR] SPOTIFY_REDIRECT_URI must be a local http URL with a port, e.g. http://127.0.0.1:8888/callback")
        return 1

    state = secrets.token_urlsafe(24)
    callback_server = CallbackServer(parsed_redirect.hostname, parsed_redirect.port, state, parsed_redirect.path)
    try:
        callback_server.start()
    except OSError as e:
        print(f"[ERROR] Could not bind callback server on {parsed_redirect.hostname}:{parsed_redirect.port}: {e}")
        return 1

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
        "show_dialog": "true",
    }
    auth_link = AUTH_URL + "?" + urllib.parse.urlencode(params)

    print("=" * 64)
    print(" Spotify OAuth Helper")
    print("=" * 64)
    print(f"Using redirect URI: {redirect_uri}")
    print(f"Client ID (tail): ...{client_id[-6:] if len(client_id) >= 6 else client_id}")
    print("Open this URL if browser does not open automatically:")
    print(auth_link)
    print()
    print("Waiting for Spotify callback...")

    try:
        webbrowser.open(auth_link)
    except Exception:
        pass

    try:
        callback_server.done.wait(timeout=180)
    finally:
        callback_server.stop()

    if not callback_server.done.is_set():
        print("[ERROR] Timed out waiting for callback.")
        return 1
    if callback_server.error:
        print(f"[ERROR] {callback_server.error}")
        print("Common fixes:")
        print("  1) Add redirect URI exactly in Spotify app settings:")
        print("     http://127.0.0.1:8888/callback")
        print("  2) In Development mode, add your Spotify account under Users and Access.")
        print("  3) Verify SPOTIFY_CLIENT_ID/SECRET are from the same app.")
        return 1
    if not callback_server.code:
        print("[ERROR] Authorization code missing.")
        return 1

    try:
        token_payload = _exchange_code_for_tokens(
            client_id=client_id,
            client_secret=client_secret,
            code=callback_server.code,
            redirect_uri=redirect_uri,
        )
    except Exception as e:
        print(f"[ERROR] Token exchange failed: {e}")
        return 1

    refresh_token = token_payload.get("refresh_token", "")
    access_token = token_payload.get("access_token", "")
    expires_in = token_payload.get("expires_in")
    scope = token_payload.get("scope", "")

    if not refresh_token:
        print("[ERROR] No refresh_token received.")
        print("If your app is in Development mode, make sure your Spotify account is added as a user in the app dashboard.")
        return 1

    print()
    print("[SUCCESS] Spotify OAuth complete.")
    print("Use these in your startup terminal/session:")
    print()
    print(f"set SPOTIFY_CLIENT_ID={client_id}")
    print(f"set SPOTIFY_CLIENT_SECRET={client_secret}")
    print(f"set SPOTIFY_REFRESH_TOKEN={refresh_token}")
    print("set SPOTIFY_QUEUE_ON_REQUEST=1")
    print()
    print(f"Scopes granted: {scope}")
    if access_token and expires_in:
        print(f"Access token lifetime: {expires_in}s")
    print()
    print("Keep your client secret and refresh token private.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
