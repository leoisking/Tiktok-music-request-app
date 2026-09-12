import asyncio
import os
import threading
import time
import copy
import re
import unicodedata
import ctypes
import random
import base64
import json
import math
import hashlib
import secrets
import ssl
import itertools
import functools
import http.client
from collections import Counter, OrderedDict
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import urllib.parse
from flask import Flask, send_file, request
from flask_socketio import SocketIO
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent
from spotify_oauth_helper import verifying_ssl_context
try:
    from TikTokLive.events import RoomUserSeqEvent
except Exception:
    RoomUserSeqEvent = None

try:
    # Changed from winsdk to winrt
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaSessionManager
    HAS_WINSDK_MEDIA = True
except Exception:
    MediaSessionManager = None
    HAS_WINSDK_MEDIA = False


def _env_int(name, default, minimum=None):
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    if minimum is not None:
        value = max(minimum, value)
    return value


def _env_float(name, default, minimum=None):
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = float(default)
    if not math.isfinite(value):
        value = float(default)
    if minimum is not None:
        value = max(minimum, value)
    return value

# Configuration
CHAT_SOURCE = os.getenv("CHAT_SOURCE", "tiktok").strip().lower()
TIKTOK_USER = os.getenv("TIKTOK_USER", "").strip()
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL", "").strip().lower().lstrip("#")
TWITCH_BOT_USERNAME = os.getenv("TWITCH_BOT_USERNAME", "").strip()
TWITCH_OAUTH_TOKEN = os.getenv("TWITCH_OAUTH_TOKEN", "").strip()
TWITCH_HOST = os.getenv("TWITCH_HOST", "irc.chat.twitch.tv").strip()
TWITCH_PORT = _env_int("TWITCH_PORT", 6697, minimum=1)
TWITCH_RECONNECT_DELAY_SEC = _env_float("TWITCH_RECONNECT_DELAY_SEC", 6.0, minimum=1.0)
SKIP_THRESHOLD = _env_int("SKIP_THRESHOLD", 10, minimum=1)
ADAPTIVE_SKIP_THRESHOLD_ENABLED = os.getenv("ADAPTIVE_SKIP_THRESHOLD_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")
ADAPTIVE_SKIP_MIN = _env_int("ADAPTIVE_SKIP_MIN", 2, minimum=1)
ADAPTIVE_SKIP_MAX = _env_int("ADAPTIVE_SKIP_MAX", 40, minimum=1)
ADAPTIVE_SKIP_RATIO = _env_float("ADAPTIVE_SKIP_RATIO", 0.08, minimum=0.01)
ADAPTIVE_SKIP_ACTIVE_WINDOW_SEC = _env_int("ADAPTIVE_SKIP_ACTIVE_WINDOW_SEC", 120, minimum=15)
ADAPTIVE_SKIP_RECALC_INTERVAL_SEC = _env_float("ADAPTIVE_SKIP_RECALC_INTERVAL_SEC", 5.0, minimum=1.0)
ADAPTIVE_SKIP_USE_VIEWER_COUNT = os.getenv("ADAPTIVE_SKIP_USE_VIEWER_COUNT", "1").strip().lower() not in ("0", "false", "no", "off")
ADAPTIVE_SKIP_VIEWER_STALE_SEC = _env_float("ADAPTIVE_SKIP_VIEWER_STALE_SEC", 45.0, minimum=5.0)
ADAPTIVE_SKIP_VIEWER_MIN_ACTIVE_CHAT = _env_int("ADAPTIVE_SKIP_VIEWER_MIN_ACTIVE_CHAT", 0, minimum=0)
ADAPTIVE_SKIP_VIEWER_CHAT_SANITY_MULT = _env_float("ADAPTIVE_SKIP_VIEWER_CHAT_SANITY_MULT", 80.0, minimum=1.0)
ADAPTIVE_SKIP_VIEWER_LOW_MAX = _env_int("ADAPTIVE_SKIP_VIEWER_LOW_MAX", 5, minimum=1)
ADAPTIVE_SKIP_VIEWER_LOW_THRESHOLD = _env_int("ADAPTIVE_SKIP_VIEWER_LOW_THRESHOLD", 2, minimum=1)
ADAPTIVE_SKIP_VIEWER_MID_MAX = _env_int("ADAPTIVE_SKIP_VIEWER_MID_MAX", 9, minimum=1)
ADAPTIVE_SKIP_VIEWER_MID_THRESHOLD = _env_int("ADAPTIVE_SKIP_VIEWER_MID_THRESHOLD", 3, minimum=1)
ADAPTIVE_SKIP_VIEWER_HIGH_MIN = _env_int("ADAPTIVE_SKIP_VIEWER_HIGH_MIN", 5, minimum=1)
ADAPTIVE_SKIP_VIEWER_RATIO = _env_float("ADAPTIVE_SKIP_VIEWER_RATIO", 0.50, minimum=0.01)
if ADAPTIVE_SKIP_MIN > ADAPTIVE_SKIP_MAX:
    ADAPTIVE_SKIP_MIN, ADAPTIVE_SKIP_MAX = ADAPTIVE_SKIP_MAX, ADAPTIVE_SKIP_MIN
if ADAPTIVE_SKIP_VIEWER_MID_MAX < ADAPTIVE_SKIP_VIEWER_LOW_MAX:
    ADAPTIVE_SKIP_VIEWER_MID_MAX = ADAPTIVE_SKIP_VIEWER_LOW_MAX
CONTROL_PASSWORD = os.getenv("CONTROL_PASSWORD", "")
if CONTROL_PASSWORD in ("your_password", "your_secure_pass", "YourSecurePassword"):
    CONTROL_PASSWORD = ""
HOST = os.getenv("HOST", "127.0.0.1").strip() or "127.0.0.1"
PORT = _env_int("PORT", 5000, minimum=1)
ALLOWED_ORIGINS = [origin.strip().rstrip("/") for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()]
if "*" in ALLOWED_ORIGINS:
    raise ValueError("ALLOWED_ORIGINS must contain exact origins, not '*'. Leave it unset for same-origin overlays.")
MOD_LIST = [m.strip() for m in os.getenv("MOD_LIST", "").split(",") if m.strip()]
MAX_QUEUE_SIZE = _env_int("MAX_QUEUE_SIZE", 200, minimum=10)
MAX_MESSAGE_LEN = _env_int("MAX_MESSAGE_LEN", 280, minimum=20)
QUEUE_MAX_AGE_MINUTES = _env_int("QUEUE_MAX_AGE_MINUTES", 240, minimum=0)
AUTO_RESET_SKIP_ENABLED = os.getenv("AUTO_RESET_SKIP_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")
AUTO_RESET_SKIP_DELAY_SEC = _env_int("AUTO_RESET_SKIP_DELAY_SEC", 2, minimum=0)
AUTO_NEXT_ON_THRESHOLD = os.getenv("AUTO_NEXT_ON_THRESHOLD", "1").strip().lower() not in ("0", "false", "no", "off")
SPOTIFY_TRACK_WATCHER_ENABLED = os.getenv("SPOTIFY_TRACK_WATCHER_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")
SPOTIFY_TRACK_POLL_SEC = _env_float("SPOTIFY_TRACK_POLL_SEC", 2.0, minimum=0.5)
SPOTIFY_QUEUE_POLL_SEC = _env_float("SPOTIFY_QUEUE_POLL_SEC", 1.5, minimum=0.75)
SPOTIFY_OPTIMISTIC_QUEUE_TTL_SEC = _env_float("SPOTIFY_OPTIMISTIC_QUEUE_TTL_SEC", 8.0, minimum=1.0)
SPOTIFY_HTTP_TIMEOUT_SEC = _env_float("SPOTIFY_HTTP_TIMEOUT_SEC", 12.0, minimum=1.0)
SPOTIFY_DEVICE_CACHE_TTL_SEC = _env_float("SPOTIFY_DEVICE_CACHE_TTL_SEC", 300.0, minimum=5.0)
SPOTIFY_ALBUM_ART_MISS_TTL_SEC = _env_float("SPOTIFY_ALBUM_ART_MISS_TTL_SEC", 60.0, minimum=5.0)
SPOTIFY_SEARCH_PARALLELISM = _env_int("SPOTIFY_SEARCH_PARALLELISM", 4, minimum=1)
SPOTIFY_NOW_PLAYING_MISS_THRESHOLD = _env_int("SPOTIFY_NOW_PLAYING_MISS_THRESHOLD", 3, minimum=1)
SPOTIFY_QUEUE_ON_REQUEST = os.getenv("SPOTIFY_QUEUE_ON_REQUEST", "1").strip().lower() not in ("0", "false", "no", "off")
SPOTIFY_QUEUE_MANUAL_ONLY = os.getenv("SPOTIFY_QUEUE_MANUAL_ONLY", "1").strip().lower() not in ("0", "false", "no", "off")
SPOTIFY_MANUAL_QUEUE_TRACK_CAP = _env_int("SPOTIFY_MANUAL_QUEUE_TRACK_CAP", 600, minimum=50)
SPOTIFY_MANUAL_QUEUE_STATE_FILE = os.getenv("SPOTIFY_MANUAL_QUEUE_STATE_FILE", "spotify_manual_queue_state.json").strip()
SPOTIFY_MANUAL_QUEUE_BOOTSTRAP_ENABLED = os.getenv("SPOTIFY_MANUAL_QUEUE_BOOTSTRAP_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")
SPOTIFY_MANUAL_QUEUE_BOOTSTRAP_LIMIT = _env_int("SPOTIFY_MANUAL_QUEUE_BOOTSTRAP_LIMIT", 2, minimum=1)
SPOTIFY_MANUAL_QUEUE_HEAD_FALLBACK_LIMIT = _env_int("SPOTIFY_MANUAL_QUEUE_HEAD_FALLBACK_LIMIT", 2, minimum=0)
SPOTIFY_MANUAL_QUEUE_AUTO_TRACK_NEW = os.getenv("SPOTIFY_MANUAL_QUEUE_AUTO_TRACK_NEW", "1").strip().lower() not in ("0", "false", "no", "off")
SPOTIFY_MANUAL_QUEUE_AUTO_TRACK_MAX_PER_POLL = _env_int("SPOTIFY_MANUAL_QUEUE_AUTO_TRACK_MAX_PER_POLL", 4, minimum=1)
SPOTIFY_SEARCH_MARKET = os.getenv("SPOTIFY_SEARCH_MARKET", "US").strip().upper()
SPOTIFY_SEARCH_CANDIDATE_LIMIT = _env_int("SPOTIFY_SEARCH_CANDIDATE_LIMIT", 8, minimum=1)
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
SPOTIFY_REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN", "").strip()
SPOTIFY_DEVICE_ID = os.getenv("SPOTIFY_DEVICE_ID", "").strip()
REQUEST_COOLDOWN_SEC = _env_float("REQUEST_COOLDOWN_SEC", 8.0, minimum=0.0)
REQUEST_DUPLICATE_WINDOW_SEC = _env_float("REQUEST_DUPLICATE_WINDOW_SEC", 120.0, minimum=0.0)
CHAT_LOG_ALL_MESSAGES = os.getenv("CHAT_LOG_ALL_MESSAGES", "0").strip().lower() in ("1", "true", "yes", "on")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY") or secrets.token_hex(32),
    MAX_CONTENT_LENGTH=16 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
)
socketio = SocketIO(app, cors_allowed_origins=ALLOWED_ORIGINS or None,
                    max_http_buffer_size=16 * 1024, async_mode="threading")


def _initial_skip_threshold():
    if not ADAPTIVE_SKIP_THRESHOLD_ENABLED:
        return SKIP_THRESHOLD
    return max(1, min(ADAPTIVE_SKIP_MAX, ADAPTIVE_SKIP_MIN))


def _current_threshold_mode_unlocked():
    if manual_skip_threshold_override is not None:
        return "manual"
    return "adaptive" if ADAPTIVE_SKIP_THRESHOLD_ENABLED else "fixed"


song_queue = []
skip_votes = {
    "skips": 0,
    "threshold": _initial_skip_threshold(),
    "skippers": [],
    "reached": False,
    "mode": "adaptive" if ADAPTIVE_SKIP_THRESHOLD_ENABLED else "fixed",
    "active_chat": 0,
    "viewer_count": 0,
    "viewer_source": ""
}
voted_users = set()
visibility_state = {"requests": False, "chat": True, "voting": True}
now_playing_state = {"title": "", "artist": "", "elapsed": 0, "duration": 0, "playing": False, "available": False, "album_art": ""}
spotify_queue_state = []
spotify_queue_status = {
    "auth_ready": False,
    "count": 0,
    "last_error": "",
    "updated_at": 0,
    "manual_only": SPOTIFY_QUEUE_MANUAL_ONLY,
    "manual_pending": 0,
    "head_fallback_limit": SPOTIFY_MANUAL_QUEUE_HEAD_FALLBACK_LIMIT,
    "auto_track_new": SPOTIFY_MANUAL_QUEUE_AUTO_TRACK_NEW
}
spotify_manual_queue_uris = []
spotify_manual_queue_last_saved = ""
spotify_manual_queue_bootstrap_active = False
spotify_last_raw_queue_tokens = []
last_comment_time = None
comment_count = 0
state_lock = threading.RLock()
MOD_SET = {m.lower() for m in MOD_LIST}
ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200D\uFEFF]")
skip_reset_timer = None
last_queue_prune_time = 0.0
spotify_watcher_started = False
spotify_queue_poller_started = False
twitch_listener_started = False
twitch_anon_nick = f"justinfan{random.randint(10000, 99999)}"
spotify_token_lock = threading.RLock()
spotify_access_token = None
spotify_access_token_expire_ts = 0.0
active_chat_users = {}
last_adaptive_skip_recalc_ts = 0.0
manual_skip_threshold_override = None
live_viewer_count = 0
live_viewer_count_ts = 0.0
live_viewer_source = ""
# Tracks queued on Spotify by this app that the Spotify queue API has not confirmed yet.
spotify_optimistic_queue_items = []
# Set to wake the Spotify queue poller immediately instead of waiting for the poll interval.
spotify_queue_poll_wakeup = threading.Event()
# Single worker so Spotify queue order matches request order.
spotify_request_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="spotify-request")
# Single worker keeps chat commands ordered while keeping them off the chat client's event loop.
chat_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="chat-pipeline")
# Persistent pool so parallel search threads keep their HTTPS connections warm between requests.
spotify_search_executor = ThreadPoolExecutor(max_workers=SPOTIFY_SEARCH_PARALLELISM, thread_name_prefix="spotify-search")
# Single writer so state-file writes stay ordered and never block callers holding state_lock.
state_write_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="state-writer")
_request_id_counter = itertools.count(1)
# Per-thread keep-alive HTTPS connections to Spotify hosts (http.client is not thread-safe).
_spotify_http_local = threading.local()
_spotify_ssl_context_cache = None
spotify_device_lock = threading.Lock()
spotify_device_cache = {"id": "", "ts": 0.0}
album_art_cache = OrderedDict()
album_art_cache_lock = threading.Lock()
ALBUM_ART_CACHE_MAX = 512
request_last_by_user = {}
request_last_song_by_user = {}
last_request_cache_prune_time = 0.0
socket_rate_buckets = OrderedDict()
socket_rate_lock = threading.Lock()


def _consume_socket_budget(bucket, key, limit, window=10.0):
    now_ts = time.monotonic()
    cache_key = (bucket, key)
    with socket_rate_lock:
        started, count = socket_rate_buckets.pop(cache_key, (now_ts, 0))
        if now_ts - started >= window:
            started, count = now_ts, 0
        socket_rate_buckets[cache_key] = (started, count + 1)
        while len(socket_rate_buckets) > 4096:
            socket_rate_buckets.popitem(last=False)
        return count < limit


def socket_event_limit(limit=20):
    def decorate(handler):
        @wraps(handler)
        def limited(data=None, *extra):
            if extra or (data is not None and not isinstance(data, dict)):
                return {"error": "invalid_payload"}
            if not _consume_socket_budget(handler.__name__, request.sid, limit):
                return {"error": "rate_limited"}
            return handler(data)
        return limited
    return decorate


def _overlay_response(filename):
    html_path = os.path.join(app.root_path, filename)
    with open(html_path, encoding="utf-8") as html_file:
        html = html_file.read()
    scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", html, flags=re.DOTALL | re.IGNORECASE)
    hashes = ["'sha256-" + base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii") + "'"
              for script in scripts if script.strip()]
    response = send_file(html_path)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; base-uri 'none'; object-src 'none'; form-action 'self'; "
        "script-src 'self' https://cdnjs.cloudflare.com " + " ".join(hashes) + "; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; "
        "connect-src 'self' ws: wss:"
    )
    response.headers["Cache-Control"] = "no-store"
    if request.path == '/control' or request.args.get('controls') == '1':
        response.headers["Content-Security-Policy"] += "; frame-ancestors 'none'"
        response.headers["X-Frame-Options"] = "DENY"
    return response


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.route('/')
@app.route('/control')
def index():
    return _overlay_response('index.html')


@app.route('/queue_widget')
def queue_widget():
    return _overlay_response('queue_widget.html')


def broadcast_queue():
    try:
        with state_lock:
            prune_song_queue_unlocked()
            payload = _song_queue_payload_unlocked()
        socketio.emit('update_queue', payload)
    except:
        pass


def broadcast_votes():
    try:
        with state_lock:
            payload = copy.deepcopy(skip_votes)
        socketio.emit('update_ratings', payload)
    except:
        pass


def reset_skip_state():
    global skip_votes, voted_users, skip_reset_timer
    timer_to_cancel = None
    with state_lock:
        threshold = _compute_current_skip_threshold_unlocked(time.time())
        skip_votes = {
            "skips": 0,
            "threshold": threshold,
            "skippers": [],
            "reached": False,
            "mode": _current_threshold_mode_unlocked(),
            "active_chat": len(active_chat_users),
            "viewer_count": int(live_viewer_count or 0),
            "viewer_source": str(live_viewer_source or "")
        }
        voted_users.clear()
        timer_to_cancel = skip_reset_timer
        skip_reset_timer = None
    try:
        if timer_to_cancel and timer_to_cancel.is_alive():
            timer_to_cancel.cancel()
    except:
        pass


def broadcast_now_playing():
    try:
        with state_lock:
            payload = copy.deepcopy(now_playing_state)
        socketio.emit('update_now_playing', payload)
    except:
        pass


def broadcast_spotify_queue():
    try:
        with state_lock:
            payload = copy.deepcopy(spotify_queue_state)
        socketio.emit('update_spotify_queue', payload)
    except:
        pass


def broadcast_spotify_queue_status():
    try:
        with state_lock:
            payload = copy.deepcopy(spotify_queue_status)
        socketio.emit('update_spotify_queue_status', payload)
    except:
        pass


def broadcast_request_feedback(payload):
    try:
        if isinstance(payload, dict):
            socketio.emit('request_feedback', payload)
    except:
        pass


def request_spotify_queue_refresh():
    """Wake the Spotify queue poller so the overlay reconciles without waiting a full interval."""
    spotify_queue_poll_wakeup.set()


def wait_for_spotify_requests(timeout=None):
    """Block until every pending background Spotify resolution has finished.

    The resolver is a single FIFO worker, so once a no-op submitted now completes,
    everything submitted before it has completed too.
    """
    try:
        spotify_request_executor.submit(lambda: None).result(timeout=timeout)
        return True
    except Exception:
        return False


def _spotify_queue_item_from_result(spotify_result, requester):
    """Shape a successful queue-add result like an item from the Spotify queue API."""
    name = _safe_track_text(spotify_result.get("track_name", ""))
    artists = _safe_track_text(spotify_result.get("track_artists", ""))
    try:
        duration_ms = int(spotify_result.get("track_duration_ms", 0) or 0)
    except Exception:
        duration_ms = 0
    return {
        "song": name or "Unknown Song",
        "spotify_track": name,
        "spotify_artist": artists,
        "spotify_uri": str(spotify_result.get("track_uri", "") or "").strip(),
        "spotify_linked_uri": "",
        "spotify_key": _track_key(name, artists),
        "duration_sec": max(0, int(round(duration_ms / 1000.0))),
        "album_art": str(spotify_result.get("album_art", "") or "").strip(),
        "source": "spotify_queue",
        "user": _safe_track_text(requester),
    }


def _spotify_item_tokens(item):
    tokens = set()
    if not isinstance(item, dict):
        return tokens
    for field in ("spotify_uri", "spotify_linked_uri"):
        value = str(item.get(field, "") or "").strip()
        if value:
            tokens.add("u:" + value)
    key = str(item.get("spotify_key", "") or "").strip() or _track_key(
        item.get("spotify_track", ""), item.get("spotify_artist", "")
    )
    if key:
        tokens.add("k:" + key)
    return tokens


def _merge_optimistic_spotify_items_unlocked(items, now_ts=None):
    """Keep just-queued tracks visible until the Spotify queue confirms them or they expire.

    Caller must hold state_lock. Confirmed and expired entries are dropped from the pending list.
    """
    if now_ts is None:
        now_ts = time.time()
    if not spotify_optimistic_queue_items:
        return items
    present = set()
    for fetched in items:
        present.update(_spotify_item_tokens(fetched))
    merged = list(items)
    still_pending = []
    for pending in spotify_optimistic_queue_items:
        item = pending.get("item") if isinstance(pending, dict) else None
        if not isinstance(item, dict):
            continue
        if _spotify_item_tokens(item) & present:
            continue
        try:
            age = now_ts - float(pending.get("ts", 0) or 0)
        except Exception:
            age = SPOTIFY_OPTIMISTIC_QUEUE_TTL_SEC + 1
        if age > SPOTIFY_OPTIMISTIC_QUEUE_TTL_SEC:
            continue
        still_pending.append(pending)
        merged.append(item)
    spotify_optimistic_queue_items[:] = still_pending
    return merged


def _apply_spotify_request_result(request_id, requested_song, requester, spotify_result):
    """Enrich the local queue entry and the Spotify mirror once a background lookup finishes."""
    safe_name = safe_print_name(requester or 'Guest')
    if not isinstance(spotify_result, dict):
        spotify_result = {"ok": False, "reason": "invalid_result"}
    if not spotify_result.get("ok"):
        try:
            print(f"   Request stays local only: {requested_song} (by {safe_name})")
            print(f"   Spotify queue add skipped/failed: {spotify_result.get('reason', 'unknown_error')}")
        except Exception:
            pass
        return

    mirrored = _spotify_queue_item_from_result(spotify_result, requester)
    with state_lock:
        for item in song_queue:
            if isinstance(item, dict) and item.get('request_id') == request_id:
                if mirrored["duration_sec"] > 0:
                    item['duration_sec'] = mirrored["duration_sec"]
                item['spotify_track'] = mirrored['spotify_track']
                item['spotify_artist'] = mirrored['spotify_artist']
                item['album_art'] = mirrored['album_art']
                break
        spotify_optimistic_queue_items.append({"ts": time.time(), "item": mirrored})
        spotify_queue_state.append(mirrored)
        spotify_queue_status["count"] = len(spotify_queue_state)
    broadcast_queue()
    broadcast_spotify_queue()
    broadcast_spotify_queue_status()
    broadcast_request_feedback({
        'status': 'accepted',
        'reason': 'queued',
        'user': requester,
        'song': requested_song,
        'spotify_queued': True
    })
    request_spotify_queue_refresh()
    try:
        print(
            f"   Request queued on Spotify: "
            f"{mirrored['spotify_track'] or requested_song} - {mirrored['spotify_artist']} (by {safe_name})"
        )
        if spotify_result.get('device_id_used'):
            print(f"   Spotify device used: {spotify_result.get('device_id_used')}")
    except Exception:
        pass


def _dispatch_spotify_request(request_id, requested_song, requester):
    """Resolve and queue a request on Spotify in the background so chat never waits on the API."""
    def _job():
        try:
            result = queue_spotify_track_from_request(requested_song, requester=requester)
        except Exception as e:
            result = {"ok": False, "reason": str(e)}
        try:
            _apply_spotify_request_result(request_id, requested_song, requester, result)
        except Exception as e:
            try:
                print(f"[SPOTIFY] Failed to apply queue result: {e}")
            except Exception:
                pass
    spotify_request_executor.submit(_job)


async def _run_chat_pipeline(source, nickname, unique_id, msg, is_moderator=False):
    """Run the chat pipeline on a worker thread so the chat client's event loop never blocks."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        chat_executor,
        functools.partial(process_chat_message, source, nickname, unique_id, msg, is_moderator=is_moderator),
    )


def prune_song_queue_unlocked(now_ts=None):
    """Prune queue by age/size. Caller must hold state_lock."""
    changed = False
    if now_ts is None:
        now_ts = time.time()

    if QUEUE_MAX_AGE_MINUTES > 0:
        cutoff = now_ts - (QUEUE_MAX_AGE_MINUTES * 60)
        filtered = []
        for item in song_queue:
            if not isinstance(item, dict):
                changed = True
                continue
            ts = item.get('ts')
            try:
                ts_val = float(ts) if ts is not None else None
            except:
                ts_val = None
            if ts_val is not None and ts_val < cutoff:
                changed = True
                continue
            filtered.append(item)
        if len(filtered) != len(song_queue):
            changed = True
        song_queue[:] = filtered

    if len(song_queue) > MAX_QUEUE_SIZE:
        song_queue[:] = song_queue[-MAX_QUEUE_SIZE:]
        changed = True

    return changed


def schedule_skip_auto_reset():
    global skip_reset_timer
    if not AUTO_RESET_SKIP_ENABLED:
        return
    with state_lock:
        if skip_reset_timer and skip_reset_timer.is_alive():
            return
        t = threading.Timer(float(AUTO_RESET_SKIP_DELAY_SEC), perform_skip_auto_reset)
        t.daemon = True
        skip_reset_timer = t
        t.start()


def perform_skip_auto_reset():
    global skip_reset_timer, skip_votes, voted_users
    should_broadcast = False
    with state_lock:
        if skip_votes.get('skips', 0) >= skip_votes.get('threshold', SKIP_THRESHOLD):
            threshold = _compute_current_skip_threshold_unlocked(time.time())
            skip_votes = {
                "skips": 0,
                "threshold": threshold,
                "skippers": [],
                "reached": False,
                "mode": _current_threshold_mode_unlocked(),
                "active_chat": len(active_chat_users),
                "viewer_count": int(live_viewer_count or 0),
                "viewer_source": str(live_viewer_source or "")
            }
            voted_users.clear()
            should_broadcast = True
        skip_reset_timer = None
    if should_broadcast:
        broadcast_votes()
        try:
            print("   Skip votes auto-reset after threshold reached.")
        except:
            pass


def trigger_local_next_track():
    """Send a local media-next key press (Windows)."""
    if not AUTO_NEXT_ON_THRESHOLD:
        return False
    if os.name != "nt":
        print("[AUTO_NEXT] Unsupported OS for media-key next.")
        return False
    # Prefer direct Spotify session skip via winsdk if available.
    if HAS_WINSDK_MEDIA:
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                loop.create_task(_try_spotify_next_async_logged())
                return True

            ok = asyncio.run(_try_spotify_next_async_logged())
            if ok:
                return True
        except Exception as e:
            try:
                print(f"[AUTO_NEXT] winsdk skip path failed: {e}")
            except:
                pass

    # Fallback 1: focus Spotify window (main/pop-out) and send Ctrl+Right
    try:
        ok = _try_spotify_window_hotkey_next()
        if ok:
            print("[AUTO_NEXT] Spotify window hotkey skip succeeded.")
            return True
    except Exception as e:
        try:
            print(f"[AUTO_NEXT] Spotify window hotkey skip failed: {e}")
        except:
            pass

    # Fallback 2: media key injection
    try:
        VK_MEDIA_NEXT_TRACK = 0xB0
        KEYEVENTF_KEYUP = 0x0002
        user32 = ctypes.windll.user32
        user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 0, 0)
        user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, KEYEVENTF_KEYUP, 0)
        print("[AUTO_NEXT] Sent media next-track key.")
        return True
    except Exception as e:
        try:
            print(f"[AUTO_NEXT] Failed to send next-track key: {e}")
        except:
            pass
        return False


async def _try_spotify_next_async():
    """Try to skip next on Spotify via Windows media session API."""
    if not HAS_WINSDK_MEDIA:
        return False, "winsdk_unavailable"
    manager = await MediaSessionManager.request_async()
    if not manager:
        return False, "manager_unavailable"

    target = None
    try:
        sessions = list(manager.get_sessions())
    except Exception:
        sessions = []

    for s in sessions:
        src = _safe_track_text(getattr(s, "source_app_user_model_id", "")).lower()
        if "spotify" in src:
            target = s
            break

    if target is None:
        target = manager.get_current_session()
        if target is None:
            return False, "no_active_session"
        src = _safe_track_text(getattr(target, "source_app_user_model_id", "")).lower()
        if "spotify" not in src:
            return False, f"active_not_spotify:{src or 'unknown'}"

    try:
        result = await target.try_skip_next_async()
        ok = bool(result)
        return ok, ("ok" if ok else "skip_rejected")
    except Exception as e:
        return False, f"skip_call_error:{e}"


async def _try_spotify_next_async_logged():
    ok, reason = await _try_spotify_next_async()
    if ok:
        print("[AUTO_NEXT] Spotify session skip succeeded.")
    else:
        print(f"[AUTO_NEXT] Spotify session skip failed: {reason}")
    return ok


def _find_spotify_window_handle():
    """Find a top-level visible Spotify window handle (main or pop-out)."""
    if os.name != "nt":
        return None
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    hwnd_match = ctypes.c_void_p(0)

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    def _callback(hwnd, lparam):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True

            # Window title quick filter (fast path)
            title_len = user32.GetWindowTextLengthW(hwnd)
            if title_len <= 0:
                return True
            title_buf = ctypes.create_unicode_buffer(title_len + 1)
            user32.GetWindowTextW(hwnd, title_buf, title_len + 1)
            title = (title_buf.value or "").lower()

            pid = ctypes.c_ulong(0)
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if not pid.value:
                return True

            hproc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
            if not hproc:
                return True
            try:
                image_buf_len = ctypes.c_ulong(1024)
                image_buf = ctypes.create_unicode_buffer(1024)
                ok = kernel32.QueryFullProcessImageNameW(hproc, 0, image_buf, ctypes.byref(image_buf_len))
                if not ok:
                    return True
                exe = (image_buf.value or "").lower()
                if "spotify.exe" in exe:
                    # Prefer windows with spotify-ish titles if available.
                    if ("spotify" in title) or (" - " in title) or title:
                        hwnd_match.value = int(hwnd)
                        return False
            finally:
                kernel32.CloseHandle(hproc)
        except Exception:
            return True
        return True

    user32.EnumWindows(EnumWindowsProc(_callback), 0)
    return int(hwnd_match.value) if hwnd_match.value else None


def _try_spotify_window_hotkey_next():
    """Focus Spotify window and send Ctrl+Right (works with main/popup windows)."""
    hwnd = _find_spotify_window_handle()
    if not hwnd:
        return False

    user32 = ctypes.windll.user32
    SW_RESTORE = 9
    VK_CONTROL = 0x11
    VK_RIGHT = 0x27
    KEYEVENTF_KEYUP = 0x0002

    prev = user32.GetForegroundWindow()
    try:
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.06)
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_RIGHT, 0, 0, 0)
        user32.keybd_event(VK_RIGHT, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        return True
    finally:
        try:
            if prev:
                user32.SetForegroundWindow(prev)
        except Exception:
            pass


def _safe_track_text(value):
    try:
        return str(value or "").strip()
    except:
        return ""


def _extract_album_art_url(track_obj):
    try:
        if not isinstance(track_obj, dict):
            return ""
        album = track_obj.get("album", {})
        if not isinstance(album, dict):
            return ""
        images = album.get("images", [])
        if not isinstance(images, list) or not images:
            return ""
        for img in images:
            if isinstance(img, dict):
                url = _safe_track_text(img.get("url", ""))
                if url:
                    return url
    except:
        pass
    return ""


def _song_queue_payload_unlocked():
    payload = []
    for item in song_queue:
        if not isinstance(item, dict):
            continue
        entry = {
            'user': item.get('user', ''),
            'song': item.get('song', '')
        }
        try:
            duration_sec = int(item.get('duration_sec', 0) or 0)
        except:
            duration_sec = 0
        if duration_sec > 0:
            entry['duration_sec'] = duration_sec
        if item.get('spotify_track'):
            entry['spotify_track'] = item.get('spotify_track', '')
        if item.get('spotify_artist'):
            entry['spotify_artist'] = item.get('spotify_artist', '')
        if item.get('album_art'):
            entry['album_art'] = item.get('album_art', '')
        payload.append(entry)
    return payload


def _spotify_auth_ready():
    return bool(SPOTIFY_CLIENT_ID and SPOTIFY_REFRESH_TOKEN)


def _spotify_basic_auth_header():
    raw = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _spotify_refresh_access_token():
    global spotify_access_token, spotify_access_token_expire_ts
    if not _spotify_auth_ready():
        raise RuntimeError(
            "Spotify API credentials missing. Set SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_REFRESH_TOKEN."
        )

    body_params = {
        "client_id": SPOTIFY_CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": SPOTIFY_REFRESH_TOKEN
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if SPOTIFY_CLIENT_SECRET:
        headers["Authorization"] = _spotify_basic_auth_header()
    body = urllib.parse.urlencode(body_params).encode("utf-8")
    status, raw = _spotify_http_request(
        "accounts.spotify.com", "POST", "/api/token", body=body,
        headers=headers
    )
    text = raw.decode("utf-8", errors="ignore")
    if status >= 400:
        raise RuntimeError(f"Spotify token refresh failed ({status}): {text}")
    payload = json.loads(text) if text else {}

    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"Spotify token refresh failed: {payload}")
    expires_in = int(payload.get("expires_in", 3600))
    spotify_access_token = token
    spotify_access_token_expire_ts = time.time() + max(30, expires_in - 60)
    return spotify_access_token


def _spotify_get_access_token():
    with spotify_token_lock:
        if spotify_access_token and time.time() < spotify_access_token_expire_ts:
            return spotify_access_token
        return _spotify_refresh_access_token()


def _spotify_ssl_context():
    """One shared verifying context; SSLContext objects are safe to reuse across threads."""
    global _spotify_ssl_context_cache
    if _spotify_ssl_context_cache is None:
        _spotify_ssl_context_cache = verifying_ssl_context()
    return _spotify_ssl_context_cache


def _spotify_http_connection(host):
    conns = getattr(_spotify_http_local, "conns", None)
    if conns is None:
        conns = {}
        _spotify_http_local.conns = conns
    conn = conns.get(host)
    if conn is None:
        conn = http.client.HTTPSConnection(host, timeout=SPOTIFY_HTTP_TIMEOUT_SEC, context=_spotify_ssl_context())
        conns[host] = conn
    return conn


def _spotify_http_drop_connection(host):
    conns = getattr(_spotify_http_local, "conns", None)
    if not conns:
        return
    conn = conns.pop(host, None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


def _reset_spotify_http_pool():
    """Close this thread's cached Spotify connections."""
    conns = getattr(_spotify_http_local, "conns", None) or {}
    for host in list(conns):
        _spotify_http_drop_connection(host)


def _spotify_http_request(host, method, path, body=None, headers=None):
    """Send one HTTPS request over this thread's keep-alive connection.

    Returns (status, raw_bytes). A connection that died while idle is replaced and the
    request retried once, but only when the request was never sent or is a GET, so a
    queue POST can never be duplicated. Timeouts are not retried.
    """
    last_error = None
    for attempt in range(2):
        conn = _spotify_http_connection(host)
        sent = False
        try:
            conn.request(method, path, body=body, headers=headers or {})
            sent = True
            resp = conn.getresponse()
            raw = resp.read()
            if getattr(resp, "will_close", False):
                _spotify_http_drop_connection(host)
            return resp.status, raw
        except (http.client.HTTPException, OSError) as e:
            last_error = e
            _spotify_http_drop_connection(host)
            retry_safe = (not sent) or method.upper() == "GET"
            if attempt == 0 and retry_safe and not isinstance(e, TimeoutError):
                continue
            break
    raise RuntimeError(f"Spotify HTTPS request failed for {host}{path}: {last_error}")


def _spotify_api_request(method, path, query=None, retry_on_401=True, want_json=True):
    token = _spotify_get_access_token()
    method_upper = method.upper()
    url_path = f"/v1{path}"
    if query:
        url_path += "?" + urllib.parse.urlencode(query)
    headers = {"Authorization": f"Bearer {token}"}
    body = None
    if method_upper == "POST":
        body = b""
        headers["Content-Length"] = "0"
    status, raw = _spotify_http_request("api.spotify.com", method_upper, url_path, body=body, headers=headers)
    if status >= 400:
        if status == 401 and retry_on_401:
            with spotify_token_lock:
                _spotify_refresh_access_token()
            return _spotify_api_request(method, path, query=query, retry_on_401=False, want_json=want_json)
        err = raw.decode("utf-8", errors="ignore")
        raise RuntimeError(f"Spotify API error ({status}) on {path}: {err}")
    if want_json:
        return status, (json.loads(raw.decode("utf-8")) if raw else {})
    return status, None


def _invalidate_spotify_device_cache():
    with spotify_device_lock:
        spotify_device_cache.update({"id": "", "ts": 0.0})


def _spotify_resolve_device_id():
    """Resolve a playable device id for queue operations, caching the answer between requests."""
    # If user explicitly configured one, prefer it.
    if SPOTIFY_DEVICE_ID:
        return SPOTIFY_DEVICE_ID

    now_ts = time.time()
    with spotify_device_lock:
        cached_id = spotify_device_cache.get("id", "")
        cached_ts = float(spotify_device_cache.get("ts", 0.0) or 0.0)
    if cached_id and (now_ts - cached_ts) < SPOTIFY_DEVICE_CACHE_TTL_SEC:
        return cached_id

    device_id = _spotify_fetch_device_id()
    if device_id:
        with spotify_device_lock:
            spotify_device_cache.update({"id": device_id, "ts": now_ts})
    return device_id


def _spotify_fetch_device_id():
    status, payload = _spotify_api_request("GET", "/me/player/devices", want_json=True)
    if status != 200 or not isinstance(payload, dict):
        return ""
    devices = payload.get("devices", [])
    if not isinstance(devices, list) or not devices:
        return ""

    # Prefer active device, then first unrestricted device, then first device.
    for d in devices:
        if isinstance(d, dict) and d.get("is_active") and d.get("id"):
            return str(d.get("id"))
    for d in devices:
        if isinstance(d, dict) and not d.get("is_restricted") and d.get("id"):
            return str(d.get("id"))
    for d in devices:
        if isinstance(d, dict) and d.get("id"):
            return str(d.get("id"))
    return ""


def _split_request_song_artist(requested_song):
    text = (requested_song or "").strip()
    if not text:
        return "", ""

    by_match = re.match(r"^\s*(.*?)\s+\bby\b\s+(.+?)\s*$", text, flags=re.IGNORECASE)
    if by_match:
        return by_match.group(1).strip(), by_match.group(2).strip()

    dash_match = re.match(r"^\s*(.*?)\s*[-\u2013\u2014]\s*(.+?)\s*$", text)
    if dash_match:
        return dash_match.group(1).strip(), dash_match.group(2).strip()

    return text, ""


def _spotify_text_key(value):
    s = unicodedata.normalize("NFKC", _safe_track_text(value)).lower()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _spotify_strip_noise(value):
    s = _safe_track_text(value)
    if not s:
        return ""
    s = re.sub(
        r"\((official|lyrics?|lyric video|audio|video|live|remaster(?:d)?|sped up|slowed(?:\s*\+\s*reverb)?|nightcore)[^)]*\)",
        "",
        s,
        flags=re.IGNORECASE
    )
    s = re.sub(
        r"\[(official|lyrics?|lyric video|audio|video|live|remaster(?:d)?|sped up|slowed(?:\s*\+\s*reverb)?|nightcore)[^\]]*\]",
        "",
        s,
        flags=re.IGNORECASE
    )
    s = re.sub(r"\b(ft|feat|featuring)\.?\b.*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip(" -")
    return s


def _spotify_search_queries(requested_song):
    raw = _safe_track_text(requested_song)
    song_part, artist_part = _split_request_song_artist(raw)
    song_clean = _spotify_strip_noise(song_part or raw)
    artist_clean = _spotify_strip_noise(artist_part)

    queries = []
    if song_clean and artist_clean:
        queries.append(f'track:"{song_clean}" artist:"{artist_clean}"')
        queries.append(f"{song_clean} {artist_clean}")
    if song_part and artist_part:
        queries.append(f'track:"{song_part}" artist:"{artist_part}"')
    if song_clean:
        queries.append(song_clean)
    if song_part and song_part != song_clean:
        queries.append(song_part)
    if raw:
        queries.append(raw)

    out = []
    seen = set()
    for q in queries:
        key = _spotify_text_key(q)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(q)
    return out, song_part, artist_part


def _spotify_confident_score_floor(artist_hint):
    """Score at which a candidate is an exact title (and artist, when given) match."""
    if _spotify_text_key(_spotify_strip_noise(artist_hint or "")):
        return 180
    return 100


def _spotify_search_tracks(q):
    query_obj = {"q": q, "type": "track", "limit": SPOTIFY_SEARCH_CANDIDATE_LIMIT}
    if SPOTIFY_SEARCH_MARKET:
        query_obj["market"] = SPOTIFY_SEARCH_MARKET
    status, payload = _spotify_api_request("GET", "/search", query=query_obj, want_json=True)
    if status != 200:
        return []
    return (((payload or {}).get("tracks") or {}).get("items") or [])


def _spotify_search_tracks_safe(q):
    """Search wrapper for worker threads: returns (tracks, error_text) and never raises."""
    try:
        return _spotify_search_tracks(q), ""
    except Exception as e:
        return [], str(e)


def _spotify_track_match_score(track_obj, wanted_song, wanted_artist):
    if not isinstance(track_obj, dict):
        return -9999
    t_name = _safe_track_text(track_obj.get("name", ""))
    t_name_key = _spotify_text_key(t_name)
    artist_names = ", ".join([
        _safe_track_text(a.get("name", ""))
        for a in (track_obj.get("artists", []) if isinstance(track_obj.get("artists"), list) else [])
        if isinstance(a, dict)
    ])
    artist_key = _spotify_text_key(artist_names)
    song_key = _spotify_text_key(_spotify_strip_noise(wanted_song or ""))
    artist_hint_key = _spotify_text_key(_spotify_strip_noise(wanted_artist or ""))

    score = 0
    if song_key:
        if t_name_key == song_key:
            score += 100
        elif song_key in t_name_key:
            score += 70
        elif t_name_key and t_name_key in song_key:
            score += 45

    if artist_hint_key:
        if artist_hint_key == artist_key:
            score += 80
        elif artist_hint_key in artist_key:
            score += 55
        else:
            score -= 20

    unwanted_words = ("karaoke", "instrumental", "cover")
    if song_key and not any(w in song_key for w in unwanted_words):
        if any(w in t_name_key for w in unwanted_words):
            score -= 25

    try:
        score += int(track_obj.get("popularity", 0) or 0) // 10
    except Exception:
        pass
    return score


def queue_spotify_track_from_request(requested_song, requester=""):
    if not SPOTIFY_QUEUE_ON_REQUEST:
        return {"ok": False, "reason": "spotify_queue_on_request_disabled"}
    if not _spotify_auth_ready():
        return {"ok": False, "reason": "spotify_auth_not_configured"}

    try:
        queries, song_part, artist_part = _spotify_search_queries(requested_song)
        queries = queries[:6]
        best_track = None
        best_score = -9999
        first_search_error = ""
        confident_floor = _spotify_confident_score_floor(artist_part)

        def consider(tracks):
            nonlocal best_track, best_score
            for candidate in tracks:
                score = _spotify_track_match_score(candidate, song_part, artist_part)
                if score > best_score:
                    best_score = score
                    best_track = candidate

        # The most specific query usually wins outright; stop there when it does.
        if queries:
            tracks, err = _spotify_search_tracks_safe(queries[0])
            consider(tracks)
            first_search_error = err
        remaining = queries[1:]
        if remaining and best_score < confident_floor:
            for tracks, err in spotify_search_executor.map(_spotify_search_tracks_safe, remaining):
                consider(tracks)
                if err and not first_search_error:
                    first_search_error = err

        if not best_track:
            if first_search_error:
                return {"ok": False, "reason": first_search_error}
            return {"ok": False, "reason": "track_not_found"}

        track_uri = best_track.get("uri")
        track_name = best_track.get("name", "")
        artists = ", ".join([a.get("name", "") for a in best_track.get("artists", []) if isinstance(a, dict)]).strip()
        album_art = _extract_album_art_url(best_track)
        try:
            track_duration_ms = int(best_track.get("duration_ms", 0) or 0)
        except:
            track_duration_ms = 0
        if not track_uri:
            return {"ok": False, "reason": "track_uri_missing"}

        attempt_queries = []
        resolved_device_id = ""
        try:
            resolved_device_id = _spotify_resolve_device_id()
        except Exception as e:
            try:
                print(f"[SPOTIFY] Device resolve failed: {e}")
            except:
                pass

        if resolved_device_id:
            attempt_queries.append({"uri": track_uri, "device_id": resolved_device_id})
        attempt_queries.append({"uri": track_uri})

        last_err = ""
        queued_ok = False
        used_device_id = ""
        for qobj in attempt_queries:
            try:
                queue_status, _ = _spotify_api_request(
                    "POST",
                    "/me/player/queue",
                    query=qobj,
                    want_json=False
                )
                if queue_status in (200, 202, 204):
                    queued_ok = True
                    used_device_id = str(qobj.get("device_id", "") or "")
                    break
                last_err = f"queue_status_{queue_status}"
            except Exception as e:
                last_err = str(e)
            if qobj.get("device_id"):
                # The remembered device is gone or unusable; look it up fresh next time.
                _invalidate_spotify_device_cache()

        if not queued_ok:
            return {"ok": False, "reason": last_err or "queue_add_failed"}

        _register_manual_spotify_queue_uri(track_uri, track_name, artists, requester=requester)
        return {
            "ok": True,
            "track_uri": track_uri,
            "track_name": track_name,
            "track_artists": artists,
            "track_duration_ms": track_duration_ms,
            "device_id_used": used_device_id,
            "album_art": album_art
        }
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def _normalize_manual_queue_entry(entry):
    if isinstance(entry, dict):
        uri = str(entry.get("uri", "") or "").strip()
        key = str(entry.get("key", "") or "").strip()
        title = _safe_track_text(entry.get("title", ""))
        artist = _safe_track_text(entry.get("artist", ""))
        requester = _safe_track_text(entry.get("requester", ""))
        if (not key) and (title or artist):
            key = _track_key(title, artist)
        if not (uri or key):
            return None
        try:
            registered_ts = float(entry.get("ts", 0.0) or 0.0)
        except (TypeError, ValueError):
            registered_ts = 0.0
        return {
            "uri": uri,
            "key": key,
            "title": title,
            "artist": artist,
            "requester": requester,
            "ts": registered_ts
        }

    uri = str(entry or "").strip()
    if not uri:
        return None
    return {
        "uri": uri,
        "key": "",
        "title": "",
        "artist": "",
        "requester": "",
        "ts": 0.0
    }


def _normalize_manual_queue_entries_unlocked():
    normalized = []
    for raw in spotify_manual_queue_uris:
        e = _normalize_manual_queue_entry(raw)
        if e:
            normalized.append(e)
    if len(normalized) > SPOTIFY_MANUAL_QUEUE_TRACK_CAP:
        normalized = normalized[-SPOTIFY_MANUAL_QUEUE_TRACK_CAP:]
    spotify_manual_queue_uris[:] = normalized
    return normalized


def _queue_item_identity(item):
    """Stable identity for a queue item across relink variants."""
    if not isinstance(item, dict):
        return ""
    uri = str(item.get("spotify_uri", "") or "").strip()
    linked_uri = str(item.get("spotify_linked_uri", "") or "").strip()
    key = str(item.get("spotify_key", "") or "").strip()
    if not key:
        key = _track_key(item.get("spotify_track", ""), item.get("spotify_artist", ""))
    if uri:
        return "u:" + uri
    if linked_uri:
        return "u:" + linked_uri
    if key:
        return "k:" + key
    return ""


def _entry_tokens(entry):
    tokens = set()
    if not isinstance(entry, dict):
        return tokens
    e_uri = str(entry.get("uri", "") or "").strip()
    e_key = str(entry.get("key", "") or "").strip()
    if e_uri:
        tokens.add("u:" + e_uri)
    if e_key:
        tokens.add("k:" + e_key)
    return tokens


def _adopt_new_spotify_queue_items_unlocked(items):
    """Auto-track new queue additions detected between Spotify polls."""
    global spotify_last_raw_queue_tokens, spotify_manual_queue_bootstrap_active
    prepared = []
    for i in items:
        token = _queue_item_identity(i)
        if token:
            prepared.append(token)
    if not SPOTIFY_MANUAL_QUEUE_AUTO_TRACK_NEW:
        spotify_last_raw_queue_tokens = prepared
        if len(spotify_last_raw_queue_tokens) > SPOTIFY_MANUAL_QUEUE_TRACK_CAP:
            spotify_last_raw_queue_tokens = spotify_last_raw_queue_tokens[-SPOTIFY_MANUAL_QUEUE_TRACK_CAP:]
        return 0

    curr_tokens = prepared
    if len(curr_tokens) > SPOTIFY_MANUAL_QUEUE_TRACK_CAP:
        curr_tokens = curr_tokens[-SPOTIFY_MANUAL_QUEUE_TRACK_CAP:]

    # First snapshot establishes baseline; do not auto-adopt everything.
    if not spotify_last_raw_queue_tokens:
        spotify_last_raw_queue_tokens = curr_tokens
        return 0

    prev_counts = Counter(spotify_last_raw_queue_tokens)
    seen_counts = Counter()
    new_candidates = []
    for item in items:
        token = _queue_item_identity(item)
        if not token:
            continue
        seen_counts[token] += 1
        if seen_counts[token] > prev_counts.get(token, 0):
            new_candidates.append(item)

    spotify_last_raw_queue_tokens = curr_tokens
    if not new_candidates:
        return 0

    existing_entries = _normalize_manual_queue_entries_unlocked()
    existing_tokens = set()
    for e in existing_entries:
        existing_tokens.update(_entry_tokens(e))

    added = 0
    for item in new_candidates:
        if added >= SPOTIFY_MANUAL_QUEUE_AUTO_TRACK_MAX_PER_POLL:
            break
        candidate_token = _queue_item_identity(item)
        candidate_key = str(item.get("spotify_key", "") or "").strip() or _track_key(
            item.get("spotify_track", ""),
            item.get("spotify_artist", "")
        )
        # Skip duplicates already tracked.
        if candidate_token and candidate_token in existing_tokens:
            continue
        if candidate_key and ("k:" + candidate_key) in existing_tokens:
            continue

        entry = _normalize_manual_queue_entry({
            "uri": item.get("spotify_uri", "") or item.get("spotify_linked_uri", ""),
            "title": item.get("spotify_track", ""),
            "artist": item.get("spotify_artist", ""),
            "requester": item.get("user", "")
        })
        if not entry:
            continue

        spotify_manual_queue_uris.append(entry)
        if len(spotify_manual_queue_uris) > SPOTIFY_MANUAL_QUEUE_TRACK_CAP:
            spotify_manual_queue_uris[:] = spotify_manual_queue_uris[-SPOTIFY_MANUAL_QUEUE_TRACK_CAP:]
        existing_tokens.update(_entry_tokens(entry))
        added += 1

    if added > 0:
        spotify_manual_queue_bootstrap_active = False
        _save_manual_spotify_queue_state_unlocked()
        try:
            print(f"[SPOTIFY] Auto-tracked {added} new queue item(s) from Spotify.")
        except Exception:
            pass
    return added


def _register_manual_spotify_queue_uri(track_uri, track_name="", track_artists="", requester=""):
    global spotify_manual_queue_bootstrap_active
    entry = _normalize_manual_queue_entry({
        "uri": track_uri,
        "title": track_name,
        "artist": track_artists,
        "requester": requester,
        "ts": time.time()
    })
    if not entry:
        return
    with state_lock:
        _normalize_manual_queue_entries_unlocked()
        spotify_manual_queue_uris.append(entry)
        if len(spotify_manual_queue_uris) > SPOTIFY_MANUAL_QUEUE_TRACK_CAP:
            spotify_manual_queue_uris[:] = spotify_manual_queue_uris[-SPOTIFY_MANUAL_QUEUE_TRACK_CAP:]
        spotify_manual_queue_bootstrap_active = False
        _save_manual_spotify_queue_state_unlocked()


def _bootstrap_manual_spotify_queue_unlocked(items):
    """When tracker is empty, adopt the current top Spotify queue items."""
    global spotify_manual_queue_bootstrap_active
    if not SPOTIFY_QUEUE_MANUAL_ONLY:
        return
    if not SPOTIFY_MANUAL_QUEUE_BOOTSTRAP_ENABLED:
        return
    if spotify_manual_queue_uris:
        return
    if not isinstance(items, list) or not items:
        return

    entries = []
    for item in items:
        if not isinstance(item, dict):
            continue
        entry = _normalize_manual_queue_entry({
            "uri": item.get("spotify_uri", ""),
            "title": item.get("spotify_track", ""),
            "artist": item.get("spotify_artist", ""),
            "requester": item.get("user", "")
        })
        if not entry:
            continue
        entries.append(entry)
        if len(entries) >= SPOTIFY_MANUAL_QUEUE_BOOTSTRAP_LIMIT:
            break

    if not entries:
        return

    spotify_manual_queue_uris[:] = entries[-SPOTIFY_MANUAL_QUEUE_TRACK_CAP:]
    spotify_manual_queue_bootstrap_active = True
    _save_manual_spotify_queue_state_unlocked(force=True)
    try:
        print(f"[SPOTIFY] Manual queue bootstrap adopted {len(entries)} queue item(s).")
    except Exception:
        pass


def _filter_spotify_queue_to_manual_unlocked(items):
    """Keep only tracks explicitly queued via this app, excluding Spotify autoplay picks."""
    global spotify_manual_queue_bootstrap_active
    if not SPOTIFY_QUEUE_MANUAL_ONLY:
        return items
    if not isinstance(items, list):
        return []
    entries = _normalize_manual_queue_entries_unlocked()
    if not entries:
        return []

    expected_count = min(len(items), len(entries))
    filtered = []
    filtered_entries = []
    used = [False] * len(entries)
    for item in items:
        if not isinstance(item, dict):
            continue

        item_uri = str(item.get("spotify_uri", "") or "").strip()
        item_linked_uri = str(item.get("spotify_linked_uri", "") or "").strip()
        item_key = str(item.get("spotify_key", "") or "").strip()
        if not item_key:
            item_key = _track_key(item.get("spotify_track", ""), item.get("spotify_artist", ""))

        match_idx = -1
        for idx, entry in enumerate(entries):
            if used[idx]:
                continue
            e_uri = str(entry.get("uri", "") or "").strip()
            e_key = str(entry.get("key", "") or "").strip()

            if e_uri and (e_uri == item_uri or e_uri == item_linked_uri):
                match_idx = idx
                break
            if e_key and item_key and e_key == item_key:
                match_idx = idx
                break

        if match_idx < 0:
            continue
        used[match_idx] = True
        matched_entry = entries[match_idx]
        requester = _safe_track_text(matched_entry.get("requester", ""))
        out_item = item
        if requester and not _safe_track_text(item.get("user", "")):
            out_item = dict(item)
            out_item["user"] = requester
        filtered.append(out_item)
        filtered_entries.append(matched_entry)

    # If tracking matched only part of the real queue head, include a small head fallback
    # so manually queued songs still show even when Spotify relinks metadata.
    if (not spotify_manual_queue_bootstrap_active) and SPOTIFY_MANUAL_QUEUE_HEAD_FALLBACK_LIMIT > 0:
        target = min(
            len(items),
            max(int(SPOTIFY_MANUAL_QUEUE_HEAD_FALLBACK_LIMIT), int(expected_count))
        )
        if len(filtered) < target:
            seen_keys = set()
            for it in filtered:
                i_uri = str(it.get("spotify_uri", "") or "").strip()
                i_link = str(it.get("spotify_linked_uri", "") or "").strip()
                i_key = str(it.get("spotify_key", "") or "").strip() or _track_key(
                    it.get("spotify_track", ""),
                    it.get("spotify_artist", "")
                )
                if i_uri:
                    seen_keys.add("u:" + i_uri)
                if i_link:
                    seen_keys.add("u:" + i_link)
                if i_key:
                    seen_keys.add("k:" + i_key)

            for item in items:
                if len(filtered) >= target:
                    break
                if not isinstance(item, dict):
                    continue

                item_uri = str(item.get("spotify_uri", "") or "").strip()
                item_linked_uri = str(item.get("spotify_linked_uri", "") or "").strip()
                item_key = str(item.get("spotify_key", "") or "").strip() or _track_key(
                    item.get("spotify_track", ""),
                    item.get("spotify_artist", "")
                )

                dedupe_hit = False
                for token in (
                    ("u:" + item_uri) if item_uri else "",
                    ("u:" + item_linked_uri) if item_linked_uri else "",
                    ("k:" + item_key) if item_key else ""
                ):
                    if token and token in seen_keys:
                        dedupe_hit = True
                        break
                if dedupe_hit:
                    continue

                filtered.append(item)
                e = _normalize_manual_queue_entry({
                    "uri": item_uri or item_linked_uri,
                    "title": item.get("spotify_track", ""),
                    "artist": item.get("spotify_artist", ""),
                    "requester": item.get("user", "")
                })
                if e:
                    filtered_entries.append(e)
                    if e.get("uri", ""):
                        seen_keys.add("u:" + e.get("uri", ""))
                    if e.get("key", ""):
                        seen_keys.add("k:" + e.get("key", ""))

    # Keep entries we queued moments ago: Spotify's queue API can lag behind a successful add,
    # and dropping them here would lose the requester once the track does appear.
    now_ts = time.time()
    for idx, entry in enumerate(entries):
        if used[idx]:
            continue
        try:
            registered_ts = float(entry.get("ts", 0.0) or 0.0)
        except (TypeError, ValueError):
            registered_ts = 0.0
        if registered_ts and (now_ts - registered_ts) <= SPOTIFY_OPTIMISTIC_QUEUE_TTL_SEC:
            used[idx] = True
            filtered_entries.append(entry)

    # Reconcile expected list to what still exists in Spotify queue.
    spotify_manual_queue_uris[:] = filtered_entries[-SPOTIFY_MANUAL_QUEUE_TRACK_CAP:]
    if spotify_manual_queue_bootstrap_active and len(spotify_manual_queue_uris) > SPOTIFY_MANUAL_QUEUE_BOOTSTRAP_LIMIT:
        spotify_manual_queue_uris[:] = spotify_manual_queue_uris[:SPOTIFY_MANUAL_QUEUE_BOOTSTRAP_LIMIT]
        filtered = filtered[:SPOTIFY_MANUAL_QUEUE_BOOTSTRAP_LIMIT]
    _save_manual_spotify_queue_state_unlocked()
    return filtered


def _manual_queue_state_path():
    raw = (SPOTIFY_MANUAL_QUEUE_STATE_FILE or "spotify_manual_queue_state.json").strip()
    if not raw:
        raw = "spotify_manual_queue_state.json"
    if os.path.isabs(raw):
        return raw
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, raw)


def _write_manual_queue_state_file(path, payload):
    """Atomically write the manual queue state file. Runs on the state-writer thread."""
    global spotify_manual_queue_last_saved
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True)
        os.replace(tmp, path)
    except Exception as e:
        # Forget the last signature so the next state change retries the write.
        with state_lock:
            spotify_manual_queue_last_saved = ""
        try:
            print(f"[SPOTIFY] Failed to save manual queue state: {e}")
        except Exception:
            pass


def wait_for_background_writes(timeout=None):
    """Block until every queued state-file write has finished (single FIFO writer)."""
    try:
        state_write_executor.submit(lambda: None).result(timeout=timeout)
        return True
    except Exception:
        return False


def _save_manual_spotify_queue_state_unlocked(force=False):
    """Queue a persist of tracked manual Spotify queue entries. Caller must hold state_lock.

    The snapshot is taken here; the disk write happens on a background thread so the
    lock is never held across file I/O.
    """
    global spotify_manual_queue_last_saved
    cleaned = _normalize_manual_queue_entries_unlocked()
    mode = "bootstrap" if spotify_manual_queue_bootstrap_active else "tracked"
    sig = mode + "|" + "|".join(
        [f"{e.get('uri','')}|{e.get('key','')}|{e.get('requester','')}" for e in cleaned]
    )
    if (not force) and sig == spotify_manual_queue_last_saved:
        return

    payload = {
        "entries": copy.deepcopy(cleaned),
        "uris": [e.get("uri", "") for e in cleaned if e.get("uri", "")],  # backward compatibility
        "mode": mode,
        "updated_at": int(time.time())
    }
    spotify_manual_queue_last_saved = sig
    state_write_executor.submit(_write_manual_queue_state_file, _manual_queue_state_path(), payload)


def _load_manual_spotify_queue_state():
    """Load tracked manual Spotify queue URIs from disk. Returns loaded count."""
    global spotify_manual_queue_last_saved, spotify_manual_queue_bootstrap_active
    path = _manual_queue_state_path()
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cleaned = []
        if isinstance(data, dict):
            entries_raw = data.get("entries", [])
            if isinstance(entries_raw, list):
                for raw in entries_raw:
                    e = _normalize_manual_queue_entry(raw)
                    if e:
                        cleaned.append(e)
            if not cleaned:
                uris_raw = data.get("uris", [])
                if isinstance(uris_raw, list):
                    for raw in uris_raw:
                        e = _normalize_manual_queue_entry(raw)
                        if e:
                            cleaned.append(e)
        if len(cleaned) > SPOTIFY_MANUAL_QUEUE_TRACK_CAP:
            cleaned = cleaned[-SPOTIFY_MANUAL_QUEUE_TRACK_CAP:]
        mode = ""
        if isinstance(data, dict):
            mode = str(data.get("mode", "")).strip().lower()
        # Backward compatibility: old files without mode were bootstrap snapshots.
        bootstrap_mode = (mode == "bootstrap") or (mode == "")
        if bootstrap_mode and len(cleaned) > SPOTIFY_MANUAL_QUEUE_BOOTSTRAP_LIMIT:
            cleaned = cleaned[:SPOTIFY_MANUAL_QUEUE_BOOTSTRAP_LIMIT]
        with state_lock:
            spotify_manual_queue_uris[:] = cleaned
            spotify_manual_queue_bootstrap_active = bootstrap_mode
            spotify_manual_queue_last_saved = ("bootstrap" if bootstrap_mode else "tracked") + "|" + "|".join(
                [f"{e.get('uri','')}|{e.get('key','')}|{e.get('requester','')}" for e in cleaned]
            )
        return len(cleaned)
    except Exception as e:
        try:
            print(f"[SPOTIFY] Failed to load manual queue state: {e}")
        except Exception:
            pass
        return 0


def fetch_spotify_queue_state():
    if not _spotify_auth_ready():
        return [], "spotify_auth_not_configured"
    try:
        status, payload = _spotify_api_request(
            "GET",
            "/me/player/queue",
            want_json=True
        )
        if status != 200 or not isinstance(payload, dict):
            return [], f"spotify_queue_status_{status}"
        items = payload.get("queue", [])
        if not isinstance(items, list):
            return [], "spotify_queue_invalid_payload"
        out = []
        for item in items:
            if not isinstance(item, dict):
                continue
            uri = _safe_track_text(item.get("uri", ""))
            linked_uri = ""
            try:
                linked_uri = _safe_track_text(((item.get("linked_from") or {}).get("uri", "")))
            except Exception:
                linked_uri = ""
            name = _safe_track_text(item.get("name", ""))
            artists = ", ".join([
                _safe_track_text(a.get("name", ""))
                for a in (item.get("artists", []) if isinstance(item.get("artists"), list) else [])
                if isinstance(a, dict) and _safe_track_text(a.get("name", ""))
            ]).strip()
            try:
                duration_ms = int(item.get("duration_ms", 0) or 0)
            except:
                duration_ms = 0
            album_art = _extract_album_art_url(item)
            out.append({
                "song": name or "Unknown Song",
                "spotify_track": name,
                "spotify_artist": artists,
                "spotify_uri": uri,
                "spotify_linked_uri": linked_uri,
                "spotify_key": _track_key(name, artists),
                "duration_sec": max(0, int(round(duration_ms / 1000.0))),
                "album_art": album_art,
                "source": "spotify_queue"
            })
        with state_lock:
            _adopt_new_spotify_queue_items_unlocked(out)
            _bootstrap_manual_spotify_queue_unlocked(out)
            out = _filter_spotify_queue_to_manual_unlocked(out)
        return out, ""
    except Exception as e:
        try:
            print(f"[SPOTIFY] Queue fetch failed: {e}")
        except:
            pass
        return [], str(e)


def fetch_spotify_now_playing_state():
    """Fetch now-playing from Spotify Web API (used for album art and fallback state)."""
    if not _spotify_auth_ready():
        return None, "spotify_auth_not_configured"
    try:
        status, payload = _spotify_api_request("GET", "/me/player/currently-playing", want_json=True)
        if status == 204:
            # Fallback: /me/player often still carries item metadata when currently-playing returns 204.
            status, payload = _spotify_api_request("GET", "/me/player", want_json=True)
        if status != 200 or not isinstance(payload, dict):
            return None, f"spotify_now_status_{status}"

        item = payload.get("item", {})
        if not isinstance(item, dict):
            return None, "spotify_now_missing_item"

        title = _safe_track_text(item.get("name", ""))
        artists = ", ".join([
            _safe_track_text(a.get("name", ""))
            for a in (item.get("artists", []) if isinstance(item.get("artists"), list) else [])
            if isinstance(a, dict) and _safe_track_text(a.get("name", ""))
        ]).strip()
        try:
            duration_ms = int(item.get("duration_ms", 0) or 0)
        except:
            duration_ms = 0
        try:
            progress_ms = int(payload.get("progress_ms", 0) or 0)
        except:
            progress_ms = 0

        return {
            "title": title,
            "artist": artists,
            "duration_sec": max(0, int(round(duration_ms / 1000.0))),
            "elapsed_sec": max(0, int(round(progress_ms / 1000.0))),
            "playing": bool(payload.get("is_playing", False)),
            "album_art": _extract_album_art_url(item),
            "available": True if title or artists else False
        }, ""
    except Exception as e:
        return None, str(e)


def _reset_album_art_cache():
    with album_art_cache_lock:
        album_art_cache.clear()


def _spotify_find_album_art_for_track(title, artist):
    """Look up album art via search, remembering hits indefinitely and misses briefly."""
    t = _safe_track_text(title)
    a = _safe_track_text(artist)
    if not t and not a:
        return ""
    cache_key = _track_key(t, a) or f"{t}|{a}".lower()
    now_ts = time.time()
    with album_art_cache_lock:
        cached = album_art_cache.get(cache_key)
        if cached is not None:
            url, cached_ts = cached
            if url or (now_ts - cached_ts) < SPOTIFY_ALBUM_ART_MISS_TTL_SEC:
                album_art_cache.move_to_end(cache_key)
                return url

    q = f'track:"{t}" artist:"{a}"' if (t and a) else (t or a)
    try:
        status, payload = _spotify_api_request(
            "GET",
            "/search",
            query={"q": q, "type": "track", "limit": 1},
            want_json=True
        )
        url = ""
        if status == 200 and isinstance(payload, dict):
            items = (((payload or {}).get("tracks") or {}).get("items") or [])
            if items:
                first = items[0] if isinstance(items[0], dict) else {}
                url = _extract_album_art_url(first)
    except Exception:
        # Network trouble is not a real miss; leave it uncached so the next poll retries.
        return ""

    with album_art_cache_lock:
        album_art_cache[cache_key] = (url, now_ts)
        album_art_cache.move_to_end(cache_key)
        while len(album_art_cache) > ALBUM_ART_CACHE_MAX:
            album_art_cache.popitem(last=False)
    return url


def _spotify_queue_status_fields():
    """Status fields that are the same in every poller update. Caller must hold state_lock."""
    return {
        "updated_at": int(time.time()),
        "manual_only": SPOTIFY_QUEUE_MANUAL_ONLY,
        "manual_pending": len(spotify_manual_queue_uris),
        "manual_mode": "bootstrap" if spotify_manual_queue_bootstrap_active else "tracked",
        "head_fallback_limit": SPOTIFY_MANUAL_QUEUE_HEAD_FALLBACK_LIMIT,
        "auto_track_new": SPOTIFY_MANUAL_QUEUE_AUTO_TRACK_NEW,
    }


def _spotify_poll_once():
    """Run one Spotify poll cycle. Returns False when credentials are missing.

    All Spotify HTTP calls, including album-art searches, happen before state_lock is
    taken so a slow API never stalls chat processing.
    """
    if not _spotify_auth_ready():
        with state_lock:
            spotify_queue_state.clear()
            spotify_queue_status.update({
                "auth_ready": False,
                "count": 0,
                "last_error": "Missing SPOTIFY_CLIENT_ID/SECRET/REFRESH_TOKEN",
                **_spotify_queue_status_fields(),
            })
        broadcast_spotify_queue()
        broadcast_spotify_queue_status()
        return False

    queue_snapshot, queue_error = fetch_spotify_queue_state()
    now_snapshot, _ = fetch_spotify_now_playing_state()
    if not isinstance(now_snapshot, dict):
        now_snapshot = {}
    queue_error_text = queue_error or ""
    qel = queue_error_text.lower()
    if queue_error_text:
        if "403" in qel:
            queue_error_text = "Spotify API denied queue access (check Premium account + scopes)."
        elif "404" in qel or "no active device" in qel:
            queue_error_text = "No active Spotify device. Start playback on Spotify desktop app."
        elif "401" in qel:
            queue_error_text = "Spotify token unauthorized. Re-run OAuth helper to refresh credentials."

    spotify_now_available = bool(now_snapshot and now_snapshot.get("available"))
    fallback_art = None
    fallback_for = None
    if spotify_now_available:
        if not now_snapshot.get("album_art"):
            now_snapshot["album_art"] = _spotify_find_album_art_for_track(
                now_snapshot.get("title", ""),
                now_snapshot.get("artist", "")
            )
    else:
        # Spotify's API has no current item; if the local (winsdk) watcher does, find art for that track.
        with state_lock:
            local_available = bool(now_playing_state.get("available"))
            fallback_for = (now_playing_state.get("title", ""), now_playing_state.get("artist", ""))
        if local_available:
            fallback_art = _spotify_find_album_art_for_track(*fallback_for) or ""

    with state_lock:
        queue_snapshot = _merge_optimistic_spotify_items_unlocked(queue_snapshot)
        spotify_queue_state[:] = queue_snapshot
        spotify_queue_status.update({
            "auth_ready": True,
            "count": len(queue_snapshot),
            "last_error": queue_error_text,
            **_spotify_queue_status_fields(),
        })
        if spotify_now_available:
            if not now_playing_state.get("available"):
                now_playing_state.update({
                    "title": now_snapshot.get("title", ""),
                    "artist": now_snapshot.get("artist", ""),
                    "elapsed": now_snapshot.get("elapsed_sec", 0),
                    "duration": now_snapshot.get("duration_sec", 0),
                    "playing": now_snapshot.get("playing", False),
                    "available": True
                })
            now_playing_state["album_art"] = now_snapshot.get("album_art", "")
        elif not now_playing_state.get("available"):
            now_playing_state["album_art"] = ""
        elif fallback_art is not None and fallback_for == (
                now_playing_state.get("title", ""), now_playing_state.get("artist", "")):
            # Only apply the art if the local track has not changed while we were searching.
            now_playing_state["album_art"] = fallback_art
    broadcast_spotify_queue()
    broadcast_spotify_queue_status()
    broadcast_now_playing()
    return True


def spotify_queue_poller_loop():
    """Poll Spotify Web API queue so queue_widget mirrors Spotify desktop queue."""
    while True:
        try:
            if not _spotify_poll_once():
                time.sleep(5)
                continue
        except Exception as e:
            try:
                print(f"[SPOTIFY] Queue poller error: {e}")
            except:
                pass
            with state_lock:
                spotify_queue_state.clear()
                spotify_queue_status.update({
                    "auth_ready": _spotify_auth_ready(),
                    "count": 0,
                    "last_error": str(e),
                    **_spotify_queue_status_fields(),
                })
            broadcast_spotify_queue()
            broadcast_spotify_queue_status()
        # Sleep until the interval elapses or a request asks for an immediate refresh.
        spotify_queue_poll_wakeup.wait(SPOTIFY_QUEUE_POLL_SEC)
        spotify_queue_poll_wakeup.clear()


def _track_key(title, artist):
    t = _safe_track_text(title).lower()
    a = _safe_track_text(artist).lower()
    if not t and not a:
        return ""
    return f"{t}|{a}"


def _timespan_to_seconds(value):
    """Best-effort conversion of WinRT time span objects to seconds."""
    if value is None:
        return 0
    try:
        # datetime.timedelta-like
        return int(value.total_seconds())
    except Exception:
        pass
    try:
        # pywinrt TimeSpan often stores 100ns ticks in .duration
        return int(int(getattr(value, "duration", 0)) / 10_000_000)
    except Exception:
        pass
    try:
        return int(float(value))
    except Exception:
        return 0


def _is_playing_status(playback_info):
    try:
        status_obj = getattr(playback_info, "playback_status", None)
        status_text = str(status_obj).lower()
        if "playing" in status_text:
            return True
        # Winsdk enum value for Playing is 4 on many builds.
        try:
            if int(status_obj) == 4:
                return True
        except Exception:
            pass
        # Some wrappers expose .value
        try:
            if int(getattr(status_obj, "value", -1)) == 4:
                return True
        except Exception:
            pass
        return False
    except Exception:
        return False


async def spotify_track_watcher_loop():
    """Watch local Windows media session for Spotify track changes."""
    if not HAS_WINSDK_MEDIA:
        print("[SPOTIFY] Windows media bridge (pywinrt) not installed. Track watcher disabled.")
        print("          Install with: python -m pip install winrt-runtime winrt-Windows.Foundation winrt-Windows.Media.Control")
        return

    print("[SPOTIFY] Track watcher enabled.")
    last_key = ""
    seen_first_track = False
    miss_count = 0
    while True:
        try:
            manager = await MediaSessionManager.request_async()
            if not manager:
                miss_count += 1
                if miss_count >= SPOTIFY_NOW_PLAYING_MISS_THRESHOLD:
                    with state_lock:
                        now_playing_state.update({"title": "", "artist": "", "elapsed": 0, "duration": 0, "playing": False, "available": False, "album_art": ""})
                        spotify_queue_state.clear()
                    broadcast_now_playing()
                    broadcast_spotify_queue()
                await asyncio.sleep(SPOTIFY_TRACK_POLL_SEC)
                continue

            session = manager.get_current_session()
            if not session:
                miss_count += 1
                if miss_count >= SPOTIFY_NOW_PLAYING_MISS_THRESHOLD:
                    with state_lock:
                        now_playing_state.update({"title": "", "artist": "", "elapsed": 0, "duration": 0, "playing": False, "available": False, "album_art": ""})
                        spotify_queue_state.clear()
                    broadcast_now_playing()
                    broadcast_spotify_queue()
                await asyncio.sleep(SPOTIFY_TRACK_POLL_SEC)
                continue

            source = _safe_track_text(getattr(session, "source_app_user_model_id", ""))
            if "spotify" not in source.lower():
                miss_count += 1
                if miss_count >= SPOTIFY_NOW_PLAYING_MISS_THRESHOLD:
                    with state_lock:
                        now_playing_state.update({"title": "", "artist": "", "elapsed": 0, "duration": 0, "playing": False, "available": False, "album_art": ""})
                        spotify_queue_state.clear()
                    broadcast_now_playing()
                    broadcast_spotify_queue()
                await asyncio.sleep(SPOTIFY_TRACK_POLL_SEC)
                continue

            props = await session.try_get_media_properties_async()
            title = _safe_track_text(getattr(props, "title", ""))
            artist = _safe_track_text(getattr(props, "artist", ""))
            key = _track_key(title, artist)
            if not key:
                miss_count += 1
                if miss_count >= SPOTIFY_NOW_PLAYING_MISS_THRESHOLD:
                    with state_lock:
                        now_playing_state.update({"title": "", "artist": "", "elapsed": 0, "duration": 0, "playing": False, "available": False, "album_art": ""})
                        spotify_queue_state.clear()
                    broadcast_now_playing()
                    broadcast_spotify_queue()
                await asyncio.sleep(SPOTIFY_TRACK_POLL_SEC)
                continue

            miss_count = 0
            timeline = session.get_timeline_properties()
            playback_info = session.get_playback_info()
            pos_sec = max(0, _timespan_to_seconds(getattr(timeline, "position", None)))
            start_sec = max(0, _timespan_to_seconds(getattr(timeline, "start_time", None)))
            end_sec = max(0, _timespan_to_seconds(getattr(timeline, "end_time", None)))
            duration_sec = max(0, end_sec - start_sec) if end_sec >= start_sec else end_sec
            if duration_sec <= 0:
                duration_sec = end_sec
            playing = _is_playing_status(playback_info)

            with state_lock:
                now_playing_state.update({
                    "title": title,
                    "artist": artist,
                    "elapsed": pos_sec,
                    "duration": duration_sec,
                    "playing": playing,
                    "available": True
                })
            broadcast_now_playing()

            if not seen_first_track:
                seen_first_track = True
                last_key = key
                print(f"[SPOTIFY] Initial track: {title} - {artist}")
            elif key != last_key:
                print(f"[SPOTIFY] Track changed: {title} - {artist}")
                last_key = key
                reset_skip_state()
                broadcast_votes()
                print("[SPOTIFY] Skip votes auto-reset on track change.")

        except Exception as e:
            try:
                print(f"[SPOTIFY] Watcher error: {e}")
            except:
                pass

        await asyncio.sleep(SPOTIFY_TRACK_POLL_SEC)


def start_spotify_watcher():
    global spotify_watcher_started
    if not SPOTIFY_TRACK_WATCHER_ENABLED:
        print("[SPOTIFY] Track watcher disabled by config.")
        return
    if spotify_watcher_started:
        return
    spotify_watcher_started = True

    def _runner():
        try:
            asyncio.run(spotify_track_watcher_loop())
        except Exception as e:
            try:
                print(f"[SPOTIFY] Watcher stopped: {e}")
            except:
                pass

    threading.Thread(target=_runner, daemon=True).start()


def start_spotify_queue_poller():
    global spotify_queue_poller_started
    if spotify_queue_poller_started:
        return
    spotify_queue_poller_started = True

    def _runner():
        try:
            spotify_queue_poller_loop()
        except Exception as e:
            try:
                print(f"[SPOTIFY] Queue poller stopped: {e}")
            except:
                pass

    threading.Thread(target=_runner, daemon=True).start()

def _is_authorized_action(data):
    """Require a configured password, including for local tunnel connections."""
    if not CONTROL_PASSWORD or not isinstance(data, dict):
        return False
    password = data.get('password') or data.get('token')
    if not isinstance(password, str) or len(password) > 1024:
        return False
    if not _consume_socket_budget('authentication', request.remote_addr, 60, window=60.0):
        return False
    try:
        return secrets.compare_digest(password.encode('utf-8'), CONTROL_PASSWORD.encode('utf-8'))
    except UnicodeError:
        return False


@socketio.on('mod_auth')
@socket_event_limit()
def handle_mod_auth(data=None):
    if not _is_authorized_action(data):
        return {'error': 'unauthorized'}
    return {'success': True}


# --- SOCKET.IO: moderator handlers for control panel / index.html ---
@socketio.on('mod_clear')
@socket_event_limit()
def handle_mod_clear(data=None):
    """Clear the song queue (triggered by moderator control panel)."""
    global song_queue
    sid = None
    try:
        sid = request.sid
    except:
        sid = None

    if not _is_authorized_action(data):
        try:
            print(f"[MOD_CLEAR] Unauthorized mod_clear attempt from {sid} / {getattr(request, 'remote_addr', None)}")
        except:
            print("[MOD_CLEAR] Unauthorized attempt")
        return {'error': 'unauthorized'}

    try:
        with state_lock:
            song_queue.clear()
        broadcast_queue()
        try:
            print(f"[MOD_CLEAR] Queue cleared by client: {sid}")
        except:
            print("[MOD_CLEAR] Queue cleared")
        return {'success': True}
    except Exception as e:
        try:
            print(f"[MOD_CLEAR] Error clearing queue: {e}")
        except:
            pass
        return {'error': 'internal_error'}


@socketio.on('set_visibility')
@socket_event_limit()
def handle_set_visibility(data):
    """Set panel visibility and broadcast to all clients.

    Expected shape: { requests: bool, chat: bool, voting: bool }
    """
    global visibility_state
    try:
        # Require authorization for visibility changes
        if not _is_authorized_action(data):
            try:
                print(f"[VISIBILITY] Unauthorized set_visibility attempt from {getattr(request, 'remote_addr', None)}")
            except:
                print("[VISIBILITY] Unauthorized attempt")
            return {'error': 'unauthorized'}

        if not isinstance(data, dict):
            return {'error': 'invalid_payload'}

        fields = ('requests', 'chat', 'voting')
        if any(key in data and not isinstance(data[key], bool) for key in fields):
            return {'error': 'invalid_payload'}
        with state_lock:
            for key in fields:
                if key in data:
                    visibility_state[key] = data[key]

        # Broadcast new visibility to all connected clients
        try:
            with state_lock:
                vis_payload = dict(visibility_state)
            socketio.emit('update_visibility', vis_payload)
            print(f"[VISIBILITY] Updated: {vis_payload}")
        except:
            pass

        return {'success': True}
    except Exception as e:
        try:
            print(f"[VISIBILITY] Error: {e}")
        except:
            pass
        return {'error': 'internal_error'}


@socketio.on('request_state')
@socket_event_limit(limit=4)
def handle_request_state(data=None):
    """Send current state (queue, ratings, visibility) to the requester only."""
    try:
        sid = None
        try:
            sid = request.sid
        except:
            sid = None

        # Send targeted updates
        try:
            if sid:
                with state_lock:
                    prune_song_queue_unlocked()
                    queue_payload = _song_queue_payload_unlocked()
                    votes_payload = copy.deepcopy(skip_votes)
                    vis_payload = dict(visibility_state)
                    now_payload = copy.deepcopy(now_playing_state)
                    spotify_queue_payload = copy.deepcopy(spotify_queue_state)
                    spotify_queue_status_payload = copy.deepcopy(spotify_queue_status)
                socketio.emit('update_queue', queue_payload, to=sid)
                socketio.emit('update_spotify_queue', spotify_queue_payload, to=sid)
                socketio.emit('update_spotify_queue_status', spotify_queue_status_payload, to=sid)
                socketio.emit('update_ratings', votes_payload, to=sid)
                socketio.emit('update_visibility', vis_payload, to=sid)
                socketio.emit('update_now_playing', now_payload, to=sid)
                print(f"[STATE] Sent current state to {sid}")
            else:
                # Fallback: broadcast if we don't have a sid
                with state_lock:
                    prune_song_queue_unlocked()
                    queue_payload = _song_queue_payload_unlocked()
                    votes_payload = copy.deepcopy(skip_votes)
                    vis_payload = dict(visibility_state)
                    now_payload = copy.deepcopy(now_playing_state)
                    spotify_queue_payload = copy.deepcopy(spotify_queue_state)
                    spotify_queue_status_payload = copy.deepcopy(spotify_queue_status)
                socketio.emit('update_queue', queue_payload)
                socketio.emit('update_spotify_queue', spotify_queue_payload)
                socketio.emit('update_spotify_queue_status', spotify_queue_status_payload)
                socketio.emit('update_ratings', votes_payload)
                socketio.emit('update_visibility', vis_payload)
                socketio.emit('update_now_playing', now_payload)
                print("[STATE] Sent current state (broadcast)")
        except Exception:
            pass
        return {'success': True}
    except Exception as e:
        try:
            print(f"[STATE] Error sending state: {e}")
        except:
            pass
        return {'error': 'internal_error'}


@socketio.on('simulate_comment')
@socket_event_limit(limit=10)
def handle_simulate_comment(data):
    """Simulate an incoming chat comment (for offline testing).

    Expects: { nickname: str, unique_id: str, message: str, is_moderator: bool }
    """
    try:
        # Require authorization for simulated comments (prevent hijack)
        if not _is_authorized_action(data):
            try:
                print(f"[SIMULATED] Unauthorized simulate_comment attempt from {getattr(request, 'remote_addr', None)}")
            except:
                print("[SIMULATED] Unauthorized attempt")
            return {'error': 'unauthorized'}

        if not isinstance(data, dict):
            return {'error': 'invalid_payload'}

        nickname = data.get('nickname', 'TestUser')
        unique_id = data.get('unique_id', '')
        message = data.get('message', '')
        is_mod_flag = data.get('is_moderator', False)
        if (not isinstance(nickname, str) or not isinstance(unique_id, str)
                or not isinstance(message, str) or not isinstance(is_mod_flag, bool)
                or len(nickname) > 100 or len(unique_id) > 100
                or not message.strip() or len(message) > MAX_MESSAGE_LEN):
            return {'error': 'invalid_payload'}
        nickname = normalize_message(nickname) or 'TestUser'
        unique_id = normalize_message(unique_id)
        message = normalize_message(message)

        print(f"[SIMULATED] {nickname}: {message} (mod={is_mod_flag})")

        result = process_comment(nickname, unique_id, message, is_moderator=is_mod_flag)
        try:
            feedback_payload = result.get('request_feedback') if isinstance(result, dict) else None
            if isinstance(feedback_payload, dict):
                broadcast_request_feedback(feedback_payload)
        except Exception:
            pass

        # Emit a small chat event so front-end can show the simulated message
        try:
            socketio.emit('update_chat', {'nickname': nickname, 'message': message, 'simulated': True})
        except:
            pass

        return {'success': True, 'result': result}
    except Exception as e:
        try:
            print(f"[SIMULATED] Error: {e}")
        except:
            pass
        return {'error': 'internal_error'}


@socketio.on('mod_reset')
@socket_event_limit()
def handle_mod_reset(data=None):
    """Reset skip votes (triggered by moderator control panel)."""
    global skip_votes, voted_users
    sid = None
    try:
        sid = request.sid
    except:
        sid = None

    if not _is_authorized_action(data):
        try:
            print(f"[MOD_RESET] Unauthorized mod_reset attempt from {sid} / {getattr(request, 'remote_addr', None)}")
        except:
            print("[MOD_RESET] Unauthorized attempt")
        return {'error': 'unauthorized'}

    try:
        reset_skip_state()
        broadcast_votes()
        try:
            print(f"[MOD_RESET] Skip votes reset by client: {sid}")
        except:
            print("[MOD_RESET] Skip votes reset")
        return {'success': True}
    except Exception as e:
        try:
            print(f"[MOD_RESET] Error resetting votes: {e}")
        except:
            pass
        return {'error': 'internal_error'}


@socketio.on('mod_set_threshold')
@socket_event_limit()
def handle_mod_set_threshold(data=None):
    """Set skip threshold from moderator panel (number or 'auto')."""
    sid = None
    try:
        sid = request.sid
    except:
        sid = None

    if not _is_authorized_action(data):
        try:
            print(f"[MOD_THRESHOLD] Unauthorized mod_set_threshold attempt from {sid} / {getattr(request, 'remote_addr', None)}")
        except:
            print("[MOD_THRESHOLD] Unauthorized attempt")
        return {'error': 'unauthorized'}

    if not isinstance(data, dict):
        return {'error': 'invalid_payload'}

    value = data.get('threshold')
    result = _set_skip_threshold(value)
    if not result.get("ok"):
        err = result.get("error", "invalid_threshold")
        if err == "invalid_threshold_range":
            return {'error': f'invalid_threshold_range:{result.get("min",1)}-{result.get("max",200)}'}
        return {'error': err}

    broadcast_votes()
    try:
        print(f"[MOD_THRESHOLD] Updated by {sid}: {result.get('threshold')} ({result.get('mode')})")
    except:
        pass

    if result.get("reached_now"):
        try:
            print(f"[MOD_THRESHOLD] Threshold reached immediately ({result.get('skips')}/{result.get('threshold')})")
        except:
            pass
        trigger_local_next_track()
        schedule_skip_auto_reset()

    return {
        'success': True,
        'mode': result.get('mode'),
        'threshold': result.get('threshold'),
        'skips': result.get('skips'),
        'reached': result.get('reached')
    }


def _event_value(payload, key):
    try:
        return payload.get(key) if isinstance(payload, dict) else getattr(payload, key, None)
    except Exception:
        return None


def _tiktok_user_payloads(event):
    for key in ('user_info', 'user', 'userInfo'):
        user = _event_value(event, key)
        if user is None:
            continue
        yield user
        for method in ('to_pydict', 'to_dict'):
            convert = _event_value(user, method)
            if callable(convert):
                try:
                    payload = convert()
                except Exception:
                    continue
                if isinstance(payload, dict):
                    yield payload

    for key in ('raw_data', 'as_dict', 'to_pydict', 'to_dict'):
        payload = _event_value(event, key)
        if callable(payload):
            try:
                payload = payload()
            except Exception:
                continue
        if isinstance(payload, dict):
            for user_key in ('user_info', 'user', 'userInfo'):
                user = payload.get(user_key)
                if user is not None:
                    yield user


def extract_user(event, *, prefer_stable_id=False):
    """Read account identities from object or dictionary TikTok event payloads."""
    nickname = ''
    unique_id = ''
    numeric_keys = ('userId', 'user_id', 'id', 'idStr', 'id_str')
    username_keys = ('uniqueId', 'unique_id', 'username')
    secure_keys = ('secUid', 'sec_uid')
    identity_keys = numeric_keys + secure_keys + username_keys if prefer_stable_id else username_keys + secure_keys + numeric_keys
    for payload in _tiktok_user_payloads(event):
        if not nickname:
            for key in ('nickname', 'nickName', 'nick_name', 'display_name', 'displayName', 'name'):
                value = _event_value(payload, key)
                if isinstance(value, str) and value.strip():
                    nickname = value.strip()
                    break
        if not unique_id:
            for key in identity_keys:
                value = _event_value(payload, key)
                if isinstance(value, bool) or not isinstance(value, (str, int)):
                    continue
                identity = str(value).strip()
                if not identity or identity == '0':
                    continue
                if key in numeric_keys and (not identity.isdecimal() or int(identity) <= 0):
                    continue
                unique_id = identity.lower()
                break
        if nickname and unique_id:
            break
    return nickname or 'Guest', unique_id
def safe_print_name(nickname):
    """Make a name safe for Windows cmd printing."""
    try:
        return nickname.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    except:
        return "User"


def normalize_message(msg):
    """Normalize chat commands so Unicode variants still match."""
    if not isinstance(msg, str):
        return ""
    s = unicodedata.normalize("NFKC", msg)
    s = ZERO_WIDTH_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def is_mod(nickname, unique_id, source="tiktok"):
    """Check platform identity, never a viewer-controlled display name."""
    if not isinstance(unique_id, str) or not unique_id.strip():
        return False
    identity = unique_id.strip().lower()
    return f"{source}:{identity}" in MOD_SET or (source == "tiktok" and identity in MOD_SET)


def _normalize_chat_source(value):
    v = (value or "").strip().lower()
    if v in ("tiktok", "twitch", "both"):
        return v
    return "tiktok"


def _chat_user_key(nickname, unique_id):
    uid = (unique_id or "").strip().lower()
    if uid:
        return uid
    nick = (nickname or "").strip().lower()
    if nick and nick != "guest":
        return f"nick:{nick}"
    return ""


def _request_user_key(nickname, unique_id):
    return _chat_user_key(nickname, unique_id)


def _current_viewer_metric_unlocked(now_ts, active_count=None):
    """Return trusted viewer metric (count, source) for adaptive skip."""
    if not ADAPTIVE_SKIP_USE_VIEWER_COUNT:
        return 0, ""
    if live_viewer_count_ts <= 0:
        return 0, ""
    if (now_ts - float(live_viewer_count_ts)) > float(ADAPTIVE_SKIP_VIEWER_STALE_SEC):
        return 0, ""

    try:
        viewer_metric = max(0, int(live_viewer_count or 0))
    except Exception:
        return 0, ""
    source = str(live_viewer_source or "")

    if active_count is None:
        active_count = len(active_chat_users)
    active_count = max(0, int(active_count or 0))

    # Require at least a little live chat activity before trusting viewer-based scaling.
    if active_count < int(ADAPTIVE_SKIP_VIEWER_MIN_ACTIVE_CHAT):
        return 0, ""

    # Guard against cumulative/total-view counters pretending to be live viewers.
    if active_count > 0:
        max_reasonable = int(math.ceil(active_count * float(ADAPTIVE_SKIP_VIEWER_CHAT_SANITY_MULT)))
        if viewer_metric > max_reasonable:
            return 0, ""

    return viewer_metric, source


def _viewer_based_skip_target(viewer_count):
    """Piecewise viewer target to prevent low-threshold skip abuse."""
    v = max(0, int(viewer_count or 0))
    if v <= ADAPTIVE_SKIP_VIEWER_LOW_MAX:
        return max(1, int(ADAPTIVE_SKIP_VIEWER_LOW_THRESHOLD))
    if v <= ADAPTIVE_SKIP_VIEWER_MID_MAX:
        return max(1, int(ADAPTIVE_SKIP_VIEWER_MID_THRESHOLD))
    return max(
        int(ADAPTIVE_SKIP_VIEWER_HIGH_MIN),
        int(math.ceil(v * float(ADAPTIVE_SKIP_VIEWER_RATIO)))
    )


def _compute_current_skip_threshold_unlocked(now_ts):
    """Compute threshold from active chat size. Caller must hold state_lock."""
    if manual_skip_threshold_override is not None:
        try:
            return max(1, int(manual_skip_threshold_override))
        except Exception:
            pass
    if not ADAPTIVE_SKIP_THRESHOLD_ENABLED:
        return SKIP_THRESHOLD

    cutoff = now_ts - float(ADAPTIVE_SKIP_ACTIVE_WINDOW_SEC)
    stale_keys = [k for k, ts in active_chat_users.items() if float(ts) < cutoff]
    for k in stale_keys:
        active_chat_users.pop(k, None)

    active_count = len(active_chat_users)
    dynamic_target = int(math.ceil(active_count * float(ADAPTIVE_SKIP_RATIO)))
    viewer_count, _viewer_source = _current_viewer_metric_unlocked(now_ts, active_count=active_count)
    if viewer_count > 0:
        viewer_target = _viewer_based_skip_target(viewer_count)
        dynamic_target = max(dynamic_target, viewer_target)
    dynamic_target = max(ADAPTIVE_SKIP_MIN, dynamic_target)
    dynamic_target = min(ADAPTIVE_SKIP_MAX, dynamic_target)
    return max(1, dynamic_target)


def _maybe_refresh_skip_threshold(now_ts, force=False):
    """Recalculate skip threshold from active chat and update votes if changed."""
    global last_adaptive_skip_recalc_ts

    changed = False
    reached_now = False
    with state_lock:
        if ADAPTIVE_SKIP_THRESHOLD_ENABLED:
            if not force and (now_ts - last_adaptive_skip_recalc_ts) < float(ADAPTIVE_SKIP_RECALC_INTERVAL_SEC):
                return False, False
            threshold = _compute_current_skip_threshold_unlocked(now_ts)
            last_adaptive_skip_recalc_ts = now_ts
        else:
            threshold = SKIP_THRESHOLD

        prev_threshold = int(skip_votes.get('threshold', SKIP_THRESHOLD) or SKIP_THRESHOLD)
        if threshold != prev_threshold:
            skip_votes['threshold'] = threshold
            changed = True
        mode = _current_threshold_mode_unlocked()
        if skip_votes.get('mode') != mode:
            skip_votes['mode'] = mode
            changed = True
        skip_votes['active_chat'] = len(active_chat_users)
        viewer_metric, viewer_source = _current_viewer_metric_unlocked(now_ts, active_count=skip_votes['active_chat'])
        skip_votes['viewer_count'] = viewer_metric
        skip_votes['viewer_source'] = viewer_source

        # If threshold lowered beneath current votes, treat as immediately reached.
        current_skips = int(skip_votes.get('skips', 0) or 0)
        was_reached = bool(skip_votes.get('reached'))
        is_reached = current_skips >= int(skip_votes.get('threshold', SKIP_THRESHOLD))
        skip_votes['reached'] = is_reached
        if (not was_reached) and is_reached:
            reached_now = True
            changed = True

    return changed, reached_now


def _apply_skip_threshold_unlocked(new_threshold):
    """Apply a threshold and return True if it newly reaches threshold."""
    threshold = max(1, int(new_threshold))
    prev_reached = bool(skip_votes.get('reached'))
    current_skips = int(skip_votes.get('skips', 0) or 0)
    skip_votes['threshold'] = threshold
    skip_votes['reached'] = current_skips >= threshold
    skip_votes['mode'] = _current_threshold_mode_unlocked()
    skip_votes['active_chat'] = len(active_chat_users)
    viewer_metric, viewer_source = _current_viewer_metric_unlocked(time.time(), active_count=skip_votes['active_chat'])
    skip_votes['viewer_count'] = viewer_metric
    skip_votes['viewer_source'] = viewer_source
    return (not prev_reached) and bool(skip_votes['reached'])


def _parse_compact_count(value):
    """Parse counts like 123, '1,234', '1.2K', '2M'."""
    if value is None:
        return None
    try:
        return max(0, int(value))
    except Exception:
        pass
    text = str(value).strip().upper().replace(",", "")
    if not text:
        return None
    m = re.match(r"^(\d+(?:\.\d+)?)\s*([KMB])?$", text)
    if not m:
        return None
    num = float(m.group(1))
    suffix = m.group(2) or ""
    mult = 1
    if suffix == "K":
        mult = 1_000
    elif suffix == "M":
        mult = 1_000_000
    elif suffix == "B":
        mult = 1_000_000_000
    return max(0, int(round(num * mult)))


def _extract_viewer_count_from_room_seq_event(event):
    """Best-effort extraction of current viewer count from TikTok room events."""
    values = {}
    keys_by_priority = (
        "online_user_count",
        "room_user_count",
        "viewer_count",
        "m_total",
        "pop_str",
        "total_user",
        "total",
    )

    def _capture(key, raw):
        if key in values:
            return
        parsed = _parse_compact_count(raw)
        if parsed is not None and parsed >= 0:
            values[key] = parsed

    for key in ("m_total", "pop_str", "total_user"):
        try:
            _capture(key, getattr(event, key, None))
        except Exception:
            pass

    try:
        d = event.to_pydict()
        if isinstance(d, dict):
            for key in keys_by_priority:
                if key in d:
                    _capture(key, d.get(key))
    except Exception:
        pass

    m_total = values.get("m_total")
    total_user = values.get("total_user")
    if m_total is not None and total_user is not None:
        # If total_user looks cumulative and much larger, prefer m_total.
        if total_user >= (m_total * 2) and (total_user - m_total) >= 50:
            return m_total, "m_total"

    for key in keys_by_priority:
        if key in values:
            return values[key], key
    return None, ""


def update_live_viewer_count(viewer_count, source=""):
    """Update live viewer metric and force adaptive threshold refresh."""
    global live_viewer_count, live_viewer_count_ts, live_viewer_source
    try:
        count = max(0, int(viewer_count))
    except Exception:
        return
    now_ts = time.time()
    with state_lock:
        live_viewer_count = count
        live_viewer_count_ts = now_ts
        live_viewer_source = str(source or "")

    changed, reached_now = _maybe_refresh_skip_threshold(now_ts, force=True)
    if changed:
        broadcast_votes()
    if reached_now:
        trigger_local_next_track()
        schedule_skip_auto_reset()


def _set_skip_threshold(arg):
    """Set threshold from string/int arg. Returns dict with reached_now flag."""
    global manual_skip_threshold_override
    now_ts = time.time()
    raw = str(arg or "").strip().lower()
    with state_lock:
        if raw in ("auto", "adaptive", "dynamic", "default", "reset"):
            manual_skip_threshold_override = None
            target = _compute_current_skip_threshold_unlocked(now_ts)
        else:
            try:
                target = int(raw)
            except Exception:
                return {"ok": False, "error": "invalid_threshold", "value": raw}
            if target < 1 or target > 200:
                return {"ok": False, "error": "invalid_threshold_range", "min": 1, "max": 200, "value": target}
            manual_skip_threshold_override = target

        reached_now = _apply_skip_threshold_unlocked(target)
        current = int(skip_votes.get('skips', 0) or 0)
        threshold = int(skip_votes.get('threshold', SKIP_THRESHOLD) or SKIP_THRESHOLD)
        reached = bool(skip_votes.get('reached'))
        mode = skip_votes.get('mode', _current_threshold_mode_unlocked())

    return {
        "ok": True,
        "reached_now": reached_now,
        "mode": mode,
        "threshold": threshold,
        "skips": current,
        "reached": reached
    }


def _prune_request_rate_caches_unlocked(now_ts):
    """Bound memory used by rate-limit caches. Caller must hold state_lock."""
    global last_request_cache_prune_time
    if (now_ts - last_request_cache_prune_time) < 60:
        return

    # Remove stale entries first.
    stale_after = max(float(REQUEST_DUPLICATE_WINDOW_SEC), float(REQUEST_COOLDOWN_SEC), 60.0) + 60.0
    cutoff = now_ts - stale_after

    stale_users = [k for k, ts in request_last_by_user.items() if float(ts) < cutoff]
    for k in stale_users:
        request_last_by_user.pop(k, None)

    stale_songs = [k for k, ts in request_last_song_by_user.items() if float(ts) < cutoff]
    for k in stale_songs:
        request_last_song_by_user.pop(k, None)

    # Hard caps as a fallback guard.
    max_entries = 4000
    if len(request_last_by_user) > max_entries:
        for k in list(request_last_by_user.keys())[: len(request_last_by_user) - max_entries]:
            request_last_by_user.pop(k, None)
    if len(request_last_song_by_user) > max_entries:
        for k in list(request_last_song_by_user.keys())[: len(request_last_song_by_user) - max_entries]:
            request_last_song_by_user.pop(k, None)

    last_request_cache_prune_time = now_ts


def process_chat_message(source, nickname, unique_id, msg, is_moderator=False):
    """Common chat message pipeline for TikTok/Twitch comments."""
    global last_comment_time, comment_count, last_queue_prune_time

    now_ts = time.time()
    last_comment_time = now_ts
    comment_count += 1

    identity = _chat_user_key(nickname, unique_id)
    unique_id = f"{source}:{identity}" if identity else ""
    key = unique_id
    if key:
        with state_lock:
            active_chat_users[key] = now_ts

    threshold_changed, reached_now = _maybe_refresh_skip_threshold(now_ts)
    if threshold_changed:
        broadcast_votes()
    if reached_now:
        trigger_local_next_track()
        schedule_skip_auto_reset()

    # Periodic queue prune for long streams (age + size)
    if (now_ts - last_queue_prune_time) >= 60:
        changed = False
        with state_lock:
            changed = prune_song_queue_unlocked(now_ts)
        last_queue_prune_time = now_ts
        if changed:
            broadcast_queue()

    safe_name = safe_print_name(nickname or "Guest")
    should_log_chat_line = CHAT_LOG_ALL_MESSAGES
    if not should_log_chat_line:
        try:
            normalized = normalize_message(msg)
            should_log_chat_line = bool(re.search(r"(?<![A-Za-z0-9])[!\uFF01]", normalized))
        except Exception:
            should_log_chat_line = False
    if should_log_chat_line:
        try:
            print(f"[{source.upper()}] [{safe_name}]: {msg}")
            if identity.startswith('nick:'):
                print('   Account identity missing; using display-name fallback, which can share limits between identical names.')
        except Exception:
            print(f"[{source.upper()}] [User]: (message contained unprintable chars)")

    try:
        result = process_comment(nickname, unique_id, msg, is_moderator=is_moderator)
        try:
            feedback_payload = result.get('request_feedback') if isinstance(result, dict) else None
            if isinstance(feedback_payload, dict):
                broadcast_request_feedback(feedback_payload)
        except Exception:
            pass
        if should_log_chat_line or result.get('action') not in ('none', 'ignored', 'duplicate_skip'):
            try:
                print(f"   process_comment result: {result}")
                explanations = {
                    'none': 'No supported command matched. Use !skip or !req Song by Artist.',
                    'duplicate_skip': 'This viewer already voted for the current song.',
                    'threshold_already_reached': 'The skip threshold has already been reached; waiting for the next song/reset.',
                }
                explanation = explanations.get(result.get('action'))
                if result.get('reason') == 'missing_identity':
                    explanation = 'TikTok did not provide a usable viewer identity; this vote was not counted.'
                if explanation:
                    print(f"   {explanation}")
            except Exception:
                pass
        return result
    except Exception as e:
        try:
            print(f"   process_comment raised: {e}")
        except Exception:
            pass
        return {'action': 'error', 'error': str(e)}


def _parse_twitch_tags(raw_tags):
    tags = {}
    if not raw_tags:
        return tags
    for item in raw_tags.split(";"):
        if "=" in item:
            k, v = item.split("=", 1)
            tags[k] = v
    return tags


def _parse_twitch_privmsg(line):
    """Parse Twitch IRC PRIVMSG into (nickname, unique_id, message, is_mod)."""
    if " PRIVMSG " not in line:
        return None

    tags_part = ""
    rest = line
    if rest.startswith("@"):
        sp = rest.find(" ")
        if sp > 1:
            tags_part = rest[1:sp]
            rest = rest[sp + 1:]

    if not rest.startswith(":") or " :" not in rest:
        return None

    prefix_and_cmd, message = rest[1:].split(" :", 1)
    parts = prefix_and_cmd.split(" ")
    if len(parts) < 3 or parts[1] != "PRIVMSG":
        return None

    prefix = parts[0]
    if "!" in prefix:
        nickname = prefix.split("!", 1)[0]
    else:
        nickname = prefix
    account_name = nickname

    tags = _parse_twitch_tags(tags_part)
    user_id = (tags.get("user-id") or "").strip().lower()
    display_name = (tags.get("display-name") or "").strip()
    if display_name:
        nickname = display_name

    is_mod_tag = tags.get("mod") == "1"
    badges = tags.get("badges", "")
    is_broadcaster = "broadcaster/" in badges
    is_moderator = bool(is_mod_tag or is_broadcaster
                        or is_mod('', user_id, source='twitch')
                        or is_mod('', account_name, source='twitch'))
    return nickname or "Guest", user_id, message.strip(), is_moderator


async def twitch_chat_loop():
    """Connect to Twitch IRC and feed chat messages into the widget pipeline."""
    if not TWITCH_CHANNEL:
        print("[TWITCH] TWITCH_CHANNEL not configured. Listener disabled.")
        return

    channel = TWITCH_CHANNEL
    print(f"[TWITCH] Listener enabled for #{channel}")
    if not TWITCH_BOT_USERNAME:
        print(f"[TWITCH] Using anonymous read-only nick: {twitch_anon_nick}")

    while True:
        writer = None
        try:
            reader, writer = await asyncio.open_connection(TWITCH_HOST, TWITCH_PORT, ssl=ssl.create_default_context())

            if TWITCH_OAUTH_TOKEN and TWITCH_BOT_USERNAME:
                token = TWITCH_OAUTH_TOKEN
                if not token.lower().startswith("oauth:"):
                    token = f"oauth:{token}"
                writer.write(f"PASS {token}\r\n".encode("utf-8"))
                writer.write(f"NICK {TWITCH_BOT_USERNAME}\r\n".encode("utf-8"))
            else:
                writer.write(f"NICK {twitch_anon_nick}\r\n".encode("utf-8"))

            writer.write(b"CAP REQ :twitch.tv/tags twitch.tv/commands\r\n")
            writer.write(f"JOIN #{channel}\r\n".encode("utf-8"))
            await writer.drain()
            print(f"[TWITCH] Connected to #{channel}. Listening for chat commands...")

            while True:
                raw = await reader.readline()
                if not raw:
                    raise ConnectionError("Twitch IRC closed the connection")
                line = raw.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                if line.startswith("PING "):
                    payload = line.split(" ", 1)[1]
                    writer.write(f"PONG {payload}\r\n".encode("utf-8"))
                    await writer.drain()
                    continue

                parsed = _parse_twitch_privmsg(line)
                if not parsed:
                    continue

                nickname, unique_id, msg, is_moderator = parsed
                if msg:
                    await _run_chat_pipeline("twitch", nickname, unique_id, msg, is_moderator=is_moderator)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[TWITCH] Connection error: {e}")
            print(f"[TWITCH] Reconnecting in {int(TWITCH_RECONNECT_DELAY_SEC)}s...")
            await asyncio.sleep(TWITCH_RECONNECT_DELAY_SEC)
        finally:
            try:
                if writer:
                    writer.close()
                    await writer.wait_closed()
            except Exception:
                pass


def start_twitch_listener():
    global twitch_listener_started
    if twitch_listener_started:
        return
    twitch_listener_started = True

    def _runner():
        try:
            asyncio.run(twitch_chat_loop())
        except Exception as e:
            try:
                print(f"[TWITCH] Listener stopped: {e}")
            except Exception:
                pass

    threading.Thread(target=_runner, daemon=True).start()


def process_comment(nickname, unique_id, msg, is_moderator=False):
    """Process a chat message and update global state.

    Returns a dict describing the action taken.
    """
    global song_queue, skip_votes, voted_users
    try:
        if not msg or not isinstance(msg, str):
            return {'action': 'ignored'}

        safe_name = safe_print_name(nickname or 'Guest')
        nickname = normalize_message(nickname)[:100] or 'Guest'
        unique_id = normalize_message(unique_id)[:200]
        m = normalize_message(msg)
        if len(m) > MAX_MESSAGE_LEN:
            m = m[:MAX_MESSAGE_LEN]

        # Song request: supports !req / !request, full-width ! and odd spacing
        req_match = re.search(
            r"(?<![A-Za-z0-9])(?:[^A-Za-z0-9]*[!\uFF01]\s*)(?:req|request)\s+(.+?)(?:\s*[!?.,;:]+)?\s*$",
            m,
            flags=re.IGNORECASE,
        )
        if req_match:
            requested_song = req_match.group(1).strip()
            if requested_song:
                # Catch variations of instructional placeholders used to teach the chat
                placeholder_pattern = r"^(song\s*name\s*(by|and|-)\s*artist|artist\s*name\s*-\s*song\s*name|song\s*title\s*by\s*artist)$"
                if re.match(placeholder_pattern, requested_song, flags=re.IGNORECASE):
                    print(f"   Ignored instructional helper command from {safe_name}")
                    return {'action': 'ignored', 'reason': 'instructional_placeholder'}

            if requested_song:
                now_ts = time.time()
                requester_key = _request_user_key(nickname, unique_id) or normalize_message(nickname).lower() or 'guest'
                song_norm = normalize_message(requested_song).lower()

                with state_lock:
                    _prune_request_rate_caches_unlocked(now_ts)
                    existing_for_requester = any(
                        normalize_message(item.get('song', '')).lower() == song_norm
                        and str(item.get('request_key') or item.get('user', '')).lower() == requester_key.lower()
                        for item in song_queue
                    )
                    if existing_for_requester:
                        print(f"   Ignored duplicate request from {safe_name}: '{requested_song}' is already queued for this viewer.")
                        return {
                            'action': 'duplicate_request_recent',
                            'song': requested_song,
                            'request_feedback': {
                                'status': 'rejected',
                                'reason': 'duplicate_recent',
                                'user': nickname,
                                'song': requested_song
                            }
                        }
                    if requester_key:
                        if REQUEST_COOLDOWN_SEC > 0:
                            last_ts = float(request_last_by_user.get(requester_key, 0.0) or 0.0)
                            wait_sec = REQUEST_COOLDOWN_SEC - (now_ts - last_ts)
                            if wait_sec > 0:
                                return {
                                    'action': 'request_rate_limited',
                                    'wait_seconds': int(max(1, round(wait_sec))),
                                    'request_feedback': {
                                        'status': 'rejected',
                                        'reason': 'cooldown',
                                        'user': nickname,
                                        'song': requested_song,
                                        'wait_seconds': int(max(1, round(wait_sec)))
                                    }
                                }
                        if REQUEST_DUPLICATE_WINDOW_SEC > 0 and song_norm:
                            song_key = f"{requester_key}|{song_norm}"
                            last_song_ts = float(request_last_song_by_user.get(song_key, 0.0) or 0.0)
                            if (now_ts - last_song_ts) < REQUEST_DUPLICATE_WINDOW_SEC:
                                return {
                                    'action': 'duplicate_request_recent',
                                    'song': requested_song,
                                    'request_feedback': {
                                        'status': 'rejected',
                                        'reason': 'duplicate_recent',
                                        'user': nickname,
                                        'song': requested_song
                                    }
                                }
                        request_last_by_user[requester_key] = now_ts
                        if song_norm:
                            request_last_song_by_user[f"{requester_key}|{song_norm}"] = now_ts

                # Show the request on the overlay immediately; Spotify lookup happens in the background.
                request_id = next(_request_id_counter)
                queue_entry = {
                    'user': nickname, 'song': requested_song, 'ts': time.time(),
                    'request_key': requester_key, 'request_id': request_id
                }
                with state_lock:
                    song_queue.append(queue_entry)
                    prune_song_queue_unlocked()
                broadcast_queue()

                if not SPOTIFY_QUEUE_ON_REQUEST:
                    spotify_result = {"ok": False, "reason": "spotify_queue_on_request_disabled"}
                elif not _spotify_auth_ready():
                    spotify_result = {"ok": False, "reason": "spotify_auth_not_configured"}
                else:
                    spotify_result = {"ok": False, "pending": True, "reason": "resolving"}
                    _dispatch_spotify_request(request_id, requested_song, nickname)

                if spotify_result.get('pending'):
                    print(f"   Request added: {requested_song} (by {safe_name}); resolving on Spotify in background")
                else:
                    print(f"   Request added (local queue only): {requested_song} (by {safe_name})")
                    print(f"   Spotify queue add skipped: {spotify_result.get('reason', 'unknown_error')}")
                return {
                    'action': 'request',
                    'song': requested_song,
                    'user': nickname,
                    'spotify': spotify_result,
                    'request_feedback': {
                        'status': 'accepted',
                        'reason': 'queued',
                        'user': nickname,
                        'song': requested_song,
                        'spotify_queued': False,
                        'spotify_pending': bool(spotify_result.get('pending'))
                    }
                }

        # Clear queue (mods)
        if re.search(r"(?<![A-Za-z0-9])(?:[^A-Za-z0-9]*[!\uFF01]\s*)clear\s*(?:[!?.,;:]+)?\s*$", m, flags=re.IGNORECASE):
            if is_moderator:
                with state_lock:
                    song_queue.clear()
                broadcast_queue()
                print(f"   Queue cleared by {safe_name}")
                return {'action': 'clear', 'user': nickname}
            else:
                return {'action': 'unauthorized', 'command': 'clear'}

        # Reset votes (mods)
        if re.search(r"(?<![A-Za-z0-9])(?:[^A-Za-z0-9]*[!\uFF01]\s*)(?:reset|next)\s*(?:[!?.,;:]+)?\s*$", m, flags=re.IGNORECASE):
            if is_moderator:
                reset_skip_state()
                broadcast_votes()
                print(f"   Skip votes reset by {safe_name}")
                return {'action': 'reset', 'user': nickname}
            else:
                return {'action': 'unauthorized', 'command': 'reset'}

        # Adjust skip threshold live (mods)
        threshold_match = re.search(
            r"(?<![A-Za-z0-9])(?:[^A-Za-z0-9]*[!\uFF01]\s*)(?:threshold|skipthreshold)\s+(.+?)(?:\s*[!?.,;:]+)?\s*$",
            m,
            flags=re.IGNORECASE,
        )
        if threshold_match:
            if not is_moderator:
                return {'action': 'unauthorized', 'command': 'threshold'}

            arg = (threshold_match.group(1) or "").strip().lower()
            result = _set_skip_threshold(arg)
            if not result.get("ok"):
                err = result.get("error")
                if err == "invalid_threshold_range":
                    return {'action': 'invalid_threshold_range', 'min': result.get('min', 1), 'max': result.get('max', 200), 'value': result.get('value')}
                return {'action': 'invalid_threshold', 'value': arg}

            broadcast_votes()
            print(f"   Skip threshold updated by {safe_name}: {result.get('threshold')} ({result.get('mode')})")
            if result.get("reached_now"):
                print(f"   SKIP THRESHOLD REACHED! ({result.get('skips')}/{result.get('threshold')})")
                trigger_local_next_track()
                schedule_skip_auto_reset()
            return {
                'action': 'threshold_set',
                'user': nickname,
                'mode': result.get('mode'),
                'threshold': result.get('threshold'),
                'skips': result.get('skips'),
                'reached': result.get('reached')
            }

        # Skip vote
        if re.search(r"(?<![A-Za-z0-9])(?:[^A-Za-z0-9]*[!\uFF01]\s*)skip\s*(?:[!?.,;:]+)?\s*$", m, flags=re.IGNORECASE):
            # Prefer unique_id. If missing, use nickname unless it's an unknown guest.
            uid_key = (unique_id or '').strip().lower()
            nick_key = (nickname or '').strip().lower()
            key = uid_key or (nick_key if nick_key and nick_key != 'guest' else None)
            if not key:
                return {'action': 'ignored', 'reason': 'missing_identity'}

            with state_lock:
                if skip_votes.get('reached'):
                    return {'action': 'threshold_already_reached'}
                if key and key in voted_users:
                    return {'action': 'duplicate_skip'}

                if key:
                    voted_users.add(key)
                skip_votes['skips'] += 1
                skip_votes['skippers'].append(safe_name)
                if len(skip_votes['skippers']) > 5:
                    skip_votes['skippers'] = skip_votes['skippers'][-5:]
                current = skip_votes['skips']
                threshold = skip_votes['threshold']
                skip_votes['reached'] = True if current >= threshold else False
                reached = skip_votes['reached']
            print(f"   SKIP vote ({current}/{threshold}) by {safe_name} [{key or 'anon'}]")
            if reached:
                print(f"   SKIP THRESHOLD REACHED! ({current}/{threshold})")
                trigger_local_next_track()
            broadcast_votes()
            if reached:
                schedule_skip_auto_reset()
            return {'action': 'skip', 'skips': current, 'threshold': threshold, 'reached': reached}

        return {'action': 'none'}
    except Exception as e:
        try:
            print(f"   process_comment error: {e}")
        except:
            pass
        return {'action': 'error', 'error': str(e)}


def create_client_and_connect():
    """Create a fresh TikTokLive client with event handlers registered."""
    fresh_client = TikTokLiveClient(unique_id=TIKTOK_USER)
    
    @fresh_client.on(CommentEvent)
    async def on_comment(event: CommentEvent):
        try:
            # Extract user info
            nickname, unique_id = extract_user(event)
            _, voter_id = extract_user(event, prefer_stable_id=True)
            
            # Extract message
            try:
                msg = str(event.comment).strip()
            except:
                return
            
            if not msg:
                return
            await _run_chat_pipeline(
                "tiktok", nickname, voter_id, msg,
                is_moderator=is_mod(nickname, unique_id) or is_mod(nickname, voter_id),
            )

        except Exception as e:
            try:
                print(f"   Error: {e}")
            except:
                print("   Error processing comment")

    if RoomUserSeqEvent is not None:
        @fresh_client.on(RoomUserSeqEvent)
        async def on_room_user_seq(event: RoomUserSeqEvent):
            try:
                count, source = _extract_viewer_count_from_room_seq_event(event)
                if count is None:
                    return
                update_live_viewer_count(count, source=source)
            except Exception:
                pass
    
    return fresh_client

async def main():
    selected_source = _normalize_chat_source(CHAT_SOURCE)
    if selected_source in ("tiktok", "both") and not TIKTOK_USER:
        raise RuntimeError("TIKTOK_USER is empty. Set TIKTOK_USER for TikTok mode.")
    if selected_source in ("twitch", "both") and not TWITCH_CHANNEL:
        raise RuntimeError("TWITCH_CHANNEL is empty. Set TWITCH_CHANNEL for Twitch mode.")

    threading.Thread(
        target=lambda: socketio.run(
            app,
            host=HOST,
            port=PORT,
            allow_unsafe_werkzeug=True,
            log_output=False,
            use_reloader=False
        ),
        daemon=True
    ).start()

    loaded_manual_uris = _load_manual_spotify_queue_state()
    if SPOTIFY_QUEUE_MANUAL_ONLY:
        print(f"[SPOTIFY] Loaded {loaded_manual_uris} tracked manual queue items from state.")

    # Optional local Spotify watcher (Windows media session)
    start_spotify_watcher()
    # Spotify Web API queue poller (for /queue_widget "Up Next")
    start_spotify_queue_poller()
    if SPOTIFY_QUEUE_ON_REQUEST:
        print(f"[SPOTIFY] Queue-on-!req enabled. API creds: {'SET' if _spotify_auth_ready() else 'MISSING'}")
    else:
        print("[SPOTIFY] Queue-on-!req disabled by config.")
    print(
        f"[SPOTIFY] Queue widget filter: "
        f"{'manual-only' if SPOTIFY_QUEUE_MANUAL_ONLY else 'show-all'}"
    )
    print(
        f"[SPOTIFY] Auto-track new Spotify queue adds: "
        f"{'ON' if SPOTIFY_MANUAL_QUEUE_AUTO_TRACK_NEW else 'OFF'} "
        f"(max_per_poll={SPOTIFY_MANUAL_QUEUE_AUTO_TRACK_MAX_PER_POLL})"
    )
    if SPOTIFY_QUEUE_MANUAL_ONLY:
        print(
            f"[SPOTIFY] Manual queue bootstrap: "
            f"{'ON' if SPOTIFY_MANUAL_QUEUE_BOOTSTRAP_ENABLED else 'OFF'} "
            f"(limit={SPOTIFY_MANUAL_QUEUE_BOOTSTRAP_LIMIT})"
        )
        print("          Bootstrap tracks queue head only; explicit !req tracking is full-length.")
        print(f"          Head fallback limit while tracked: {SPOTIFY_MANUAL_QUEUE_HEAD_FALLBACK_LIMIT}")
    
    print("=" * 55)
    print("  MIDLIFE DISASTER - COMBINED LIVE WIDGET")
    print("=" * 55)
    print("  Server LIVE at http://127.0.0.1:5000")
    if ADAPTIVE_SKIP_THRESHOLD_ENABLED:
        print(
            f"  Skip threshold: adaptive "
            f"(min={ADAPTIVE_SKIP_MIN}, max={ADAPTIVE_SKIP_MAX}, ratio={ADAPTIVE_SKIP_RATIO:.3f}, "
            f"window={ADAPTIVE_SKIP_ACTIVE_WINDOW_SEC}s)"
        )
        if ADAPTIVE_SKIP_USE_VIEWER_COUNT:
            print(
                f"  Adaptive viewer assist: ON "
                f"(viewer_ratio={ADAPTIVE_SKIP_VIEWER_RATIO:.3f}, stale={ADAPTIVE_SKIP_VIEWER_STALE_SEC:.0f}s, "
                f"min_chat={ADAPTIVE_SKIP_VIEWER_MIN_ACTIVE_CHAT}, sanity_x={ADAPTIVE_SKIP_VIEWER_CHAT_SANITY_MULT:.0f})"
            )
            print(
                f"     viewer brackets: <= {ADAPTIVE_SKIP_VIEWER_LOW_MAX} -> {ADAPTIVE_SKIP_VIEWER_LOW_THRESHOLD}, "
                f"{ADAPTIVE_SKIP_VIEWER_LOW_MAX + 1}-{ADAPTIVE_SKIP_VIEWER_MID_MAX} -> {ADAPTIVE_SKIP_VIEWER_MID_THRESHOLD}, "
                f"{ADAPTIVE_SKIP_VIEWER_MID_MAX + 1}+ -> max({ADAPTIVE_SKIP_VIEWER_HIGH_MIN}, viewers*{ADAPTIVE_SKIP_VIEWER_RATIO:.2f})"
            )
        else:
            print("  Adaptive viewer assist: OFF (chat-activity only)")
    else:
        print(f"  Skip threshold: fixed {SKIP_THRESHOLD} votes")
    print(f"  Auto next on threshold: {'ON' if AUTO_NEXT_ON_THRESHOLD else 'OFF'}")
    print(f"  Spotify track watcher: {'ON' if SPOTIFY_TRACK_WATCHER_ENABLED else 'OFF'}")
    print(f"  Spotify queue poll interval: {SPOTIFY_QUEUE_POLL_SEC:.2f}s")
    print(f"  Chat source: {selected_source}")
    print(f"  Request cooldown: {REQUEST_COOLDOWN_SEC:.1f}s")
    print(f"  Request duplicate window: {REQUEST_DUPLICATE_WINDOW_SEC:.1f}s")
    print(f"  Verbose chat logging: {'ON' if CHAT_LOG_ALL_MESSAGES else 'OFF'}")
    if selected_source in ("tiktok", "both"):
        print(f"  TikTok user: @{TIKTOK_USER}")
    if selected_source in ("twitch", "both"):
        print(f"  Twitch channel: #{TWITCH_CHANNEL}")
    print("  Commands:")
    print("     !req song by artist  -> request a song")
    print("     !skip                -> vote to skip current song")
    print("     !clear               -> clear requests (mods)")
    print("     !reset / !next       -> reset skip votes (mods)")
    print("     !threshold <n>       -> set skip threshold live (mods)")
    print("     !threshold auto      -> return to adaptive/fixed mode (mods)")
    print("=" * 55)
    print("  Waiting for live chat connection...")
    print("=" * 55)
    print()
    if not CONTROL_PASSWORD:
        print("  [WARN] Browser controls are disabled until CONTROL_PASSWORD is set.")
        print("         Use a strong, unique password, then open /control.")
        print()
    if SPOTIFY_QUEUE_ON_REQUEST and not _spotify_auth_ready():
        print("  [WARN] Spotify auto-queue is enabled but API credentials are missing.")
        print("         Set SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN.")
        print("         Scope needed: user-modify-playback-state")
        print()

    if selected_source in ("twitch", "both"):
        start_twitch_listener()

    if selected_source == "twitch":
        while True:
            await asyncio.sleep(3600)

    attempt = 0
    consecutive_failures = 0

    def on_connected():
        nonlocal consecutive_failures
        consecutive_failures = 0
        print(f"[TIKTOK] Connected to @{TIKTOK_USER}. Listening for chat commands...")

    while True:
        attempt += 1
        try:
            # Create a fresh client each time so event handlers are never stale.
            print(f"[TIKTOK] Connection attempt #{attempt}...")
            live_client = create_client_and_connect()

            await live_client.connect(callback=on_connected)
            consecutive_failures = 0

            # If connect() returns normally, the stream ended.
            print("[TIKTOK] Stream ended or connection closed.")
            print(f"         Total comments received this session: {comment_count}")
            print("         Reconnecting in 10 seconds...")
            print()
            await asyncio.sleep(10)

        except KeyboardInterrupt:
            print("\nShutting down...")
            break

        except Exception as e:
            consecutive_failures += 1
            error_msg = str(e).lower()

            if "not found" in error_msg or "not live" in error_msg or "offline" in error_msg:
                print(f"[TIKTOK] @{TIKTOK_USER} is not live yet. Widget server still running!")
                print("         Open http://127.0.0.1:5000 to preview the widget.")
                print("         Retrying in 20 seconds...")
                await asyncio.sleep(20)
            elif "rate" in error_msg or "429" in error_msg or "too many" in error_msg:
                wait_time = min(30 * max(1, consecutive_failures), 120)
                print(f"[TIKTOK] Rate limited by TikTok. Waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                print(f"[TIKTOK] Connection error: {e}")
                print("         Widget server still running at http://127.0.0.1:5000")
                print("         Retrying in 15 seconds...")
                await asyncio.sleep(15)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
