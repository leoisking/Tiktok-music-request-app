import asyncio
import http.client
import json
import os
import ssl
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import ANY, call, patch

from TikTokLive.proto import User

os.environ['ALLOWED_ORIGINS'] = ''

import live_widget as widget


SPOTIFY_OK = {
    "ok": True,
    "track_uri": "spotify:track:abc123",
    "track_name": "Resolved Song",
    "track_artists": "Resolved Artist",
    "track_duration_ms": 200000,
    "device_id_used": "",
    "album_art": "https://img.example/art.jpg",
}


def emitted(emit_mock, event_name):
    return [c.args[1] for c in emit_mock.call_args_list if c.args and c.args[0] == event_name]


class RequestPathTests(unittest.TestCase):
    def setUp(self):
        self.settings = patch.multiple(
            widget, CONTROL_PASSWORD='test-only-password', MOD_SET=set(),
            AUTO_NEXT_ON_THRESHOLD=False, AUTO_RESET_SKIP_ENABLED=False,
            SPOTIFY_QUEUE_ON_REQUEST=True, ADAPTIVE_SKIP_THRESHOLD_ENABLED=False,
            REQUEST_COOLDOWN_SEC=0.0, REQUEST_DUPLICATE_WINDOW_SEC=0.0,
        )
        self.settings.start()
        self.addCleanup(self.settings.stop)
        auth = patch.object(widget, '_spotify_auth_ready', return_value=True)
        auth.start()
        self.addCleanup(auth.stop)
        widget.song_queue.clear()
        widget.request_last_by_user.clear()
        widget.request_last_song_by_user.clear()
        widget.active_chat_users.clear()
        widget.spotify_queue_state.clear()
        widget.spotify_optimistic_queue_items.clear()
        widget.spotify_manual_queue_uris.clear()
        widget.spotify_queue_poll_wakeup.clear()
        widget.reset_skip_state()

    def test_request_is_broadcast_before_spotify_resolves(self):
        release = threading.Event()
        started = threading.Event()

        def slow_spotify(requested_song, requester=""):
            started.set()
            release.wait(5)
            return dict(SPOTIFY_OK)

        with patch.object(widget, 'queue_spotify_track_from_request', side_effect=slow_spotify), \
                patch.object(widget.socketio, 'emit') as emit:
            result = widget.process_comment('Viewer', '42', '!req Song by Artist')

            self.assertEqual(result['action'], 'request')
            self.assertEqual(result['request_feedback']['status'], 'accepted')
            self.assertEqual(len(widget.song_queue), 1)
            self.assertEqual(widget.song_queue[0]['song'], 'Song by Artist')
            self.assertNotIn('spotify_track', widget.song_queue[0])
            queue_payloads = emitted(emit, 'update_queue')
            self.assertEqual(len(queue_payloads), 1)
            self.assertEqual(queue_payloads[0][0]['song'], 'Song by Artist')

            self.assertTrue(started.wait(2))
            release.set()
            self.assertTrue(widget.wait_for_spotify_requests(timeout=5))

            entry = widget.song_queue[0]
            self.assertEqual(entry['spotify_track'], 'Resolved Song')
            self.assertEqual(entry['spotify_artist'], 'Resolved Artist')
            self.assertEqual(entry['album_art'], 'https://img.example/art.jpg')
            self.assertEqual(entry['duration_sec'], 200)
            self.assertEqual(len(emitted(emit, 'update_queue')), 2)
            feedback = emitted(emit, 'request_feedback')
            self.assertTrue(any(f.get('spotify_queued') is True for f in feedback))

    def test_failed_spotify_lookup_leaves_local_entry_in_place(self):
        with patch.object(widget, 'queue_spotify_track_from_request', return_value={"ok": False, "reason": "track_not_found"}), \
                patch.object(widget.socketio, 'emit') as emit:
            widget.process_comment('Viewer', '42', '!req Mystery Song')
            self.assertTrue(widget.wait_for_spotify_requests(timeout=5))
            self.assertEqual(len(widget.song_queue), 1)
            self.assertNotIn('spotify_track', widget.song_queue[0])
            self.assertEqual(widget.spotify_queue_state, [])
            self.assertFalse(any(f.get('spotify_queued') is True for f in emitted(emit, 'request_feedback')))

    def test_spotify_mirror_updates_immediately_after_queue_add(self):
        with patch.object(widget, 'queue_spotify_track_from_request', return_value=dict(SPOTIFY_OK)), \
                patch.object(widget.socketio, 'emit') as emit:
            widget.process_comment('Viewer', '42', '!req Song by Artist')
            self.assertTrue(widget.wait_for_spotify_requests(timeout=5))

            self.assertEqual(len(widget.spotify_queue_state), 1)
            mirrored = widget.spotify_queue_state[0]
            self.assertEqual(mirrored['spotify_uri'], 'spotify:track:abc123')
            self.assertEqual(mirrored['spotify_track'], 'Resolved Song')
            self.assertEqual(mirrored['user'], 'Viewer')
            self.assertEqual(mirrored['source'], 'spotify_queue')
            self.assertEqual(widget.spotify_queue_status['count'], 1)
            self.assertEqual(emitted(emit, 'update_spotify_queue')[-1][0]['spotify_uri'], 'spotify:track:abc123')
            self.assertTrue(widget.spotify_queue_poll_wakeup.is_set())

    def test_optimistic_items_survive_until_spotify_confirms(self):
        now = time.time()
        item = {"spotify_uri": "spotify:track:abc123", "spotify_track": "Resolved Song", "spotify_artist": "Resolved Artist",
                "spotify_key": widget._track_key("Resolved Song", "Resolved Artist"), "source": "spotify_queue"}
        widget.spotify_optimistic_queue_items.append({"ts": now, "item": item})

        merged = widget._merge_optimistic_spotify_items_unlocked([{"spotify_uri": "spotify:track:other"}], now + 1)
        self.assertEqual([i.get("spotify_uri") for i in merged], ["spotify:track:other", "spotify:track:abc123"])
        self.assertEqual(len(widget.spotify_optimistic_queue_items), 1)

        merged = widget._merge_optimistic_spotify_items_unlocked([{"spotify_uri": "spotify:track:abc123"}], now + 2)
        self.assertEqual([i.get("spotify_uri") for i in merged], ["spotify:track:abc123"])
        self.assertEqual(widget.spotify_optimistic_queue_items, [])

        widget.spotify_optimistic_queue_items.append({"ts": now, "item": item})
        merged = widget._merge_optimistic_spotify_items_unlocked([], now + widget.SPOTIFY_OPTIMISTIC_QUEUE_TTL_SEC + 1)
        self.assertEqual(merged, [])
        self.assertEqual(widget.spotify_optimistic_queue_items, [])

    def test_request_wakes_poller_instead_of_waiting_for_interval(self):
        widget.request_spotify_queue_refresh()
        self.assertTrue(widget.spotify_queue_poll_wakeup.is_set())

    def test_recently_registered_manual_entry_survives_poll_before_spotify_shows_it(self):
        other = {"spotify_uri": "spotify:track:old", "spotify_track": "Old", "spotify_artist": "X",
                 "spotify_key": widget._track_key("Old", "X"), "source": "spotify_queue"}
        with patch.multiple(widget, SPOTIFY_QUEUE_MANUAL_ONLY=True, SPOTIFY_MANUAL_QUEUE_HEAD_FALLBACK_LIMIT=0), \
                patch.object(widget, '_save_manual_spotify_queue_state_unlocked'):
            widget._register_manual_spotify_queue_uri("spotify:track:new", "Song", "Artist", requester="Viewer")
            with widget.state_lock:
                widget._filter_spotify_queue_to_manual_unlocked([other])
            self.assertEqual([e["uri"] for e in widget.spotify_manual_queue_uris], ["spotify:track:new"])
            self.assertEqual(widget.spotify_manual_queue_uris[0]["requester"], "Viewer")

            widget.spotify_manual_queue_uris[0]["ts"] = time.time() - widget.SPOTIFY_OPTIMISTIC_QUEUE_TTL_SEC - 1
            with widget.state_lock:
                widget._filter_spotify_queue_to_manual_unlocked([other])
            self.assertEqual(widget.spotify_manual_queue_uris, [])


class ChatDispatchTests(unittest.TestCase):
    def test_tiktok_comment_handler_runs_pipeline_off_the_event_loop(self):
        handlers = {}

        def register(event_type):
            def save_handler(handler):
                handlers[event_type] = handler
                return handler
            return save_handler

        seen_threads = []

        def record_thread(*args, **kwargs):
            seen_threads.append(threading.current_thread())
            return {'action': 'none'}

        with patch.object(widget, 'TikTokLiveClient', return_value=SimpleNamespace(on=register)):
            widget.create_client_and_connect()
        event = widget.CommentEvent(user_info=User(nick_name='Viewer', username='viewer', id=7), content='hello')
        with patch.object(widget, 'process_chat_message', side_effect=record_thread):
            asyncio.run(handlers[widget.CommentEvent](event))
        self.assertEqual(len(seen_threads), 1)
        self.assertIsNot(seen_threads[0], threading.main_thread())


class FakeResponse:
    def __init__(self, status, body=b'{}'):
        self.status = status
        self._body = body
        self.will_close = False

    def read(self):
        return self._body

    def getheader(self, name, default=None):
        return default


class FakeConnection:
    instances = []
    fail_next = 0

    def __init__(self, host, timeout=None, **kwargs):
        self.host = host
        self.kwargs = kwargs
        self.calls = []
        self.closed = False
        FakeConnection.instances.append(self)

    def request(self, method, url, body=None, headers=None):
        if FakeConnection.fail_next > 0:
            FakeConnection.fail_next -= 1
            raise http.client.RemoteDisconnected("stale keep-alive")
        self.calls.append((method, url))

    def getresponse(self):
        return FakeResponse(200, b'{"ok": true}')

    def close(self):
        self.closed = True


def track(name, artist, uri, popularity=50):
    return {
        "name": name, "uri": uri, "popularity": popularity, "duration_ms": 180000,
        "artists": [{"name": artist}],
        "album": {"images": [{"url": "https://img.example/" + uri.split(":")[-1], "width": 300, "height": 300}]},
    }


class SpotifyHttpTests(unittest.TestCase):
    def setUp(self):
        FakeConnection.instances = []
        FakeConnection.fail_next = 0
        widget._reset_spotify_http_pool()
        for target in (
            patch.object(widget.http.client, 'HTTPSConnection', FakeConnection),
            patch.object(widget, '_spotify_get_access_token', return_value='token'),
        ):
            target.start()
            self.addCleanup(target.stop)

    def api_connections(self):
        return [c for c in FakeConnection.instances if c.host == 'api.spotify.com']

    def test_sequential_api_calls_reuse_one_connection(self):
        widget._spotify_api_request("GET", "/me/player/queue")
        status, payload = widget._spotify_api_request("GET", "/me/player/currently-playing")
        self.assertEqual((status, payload), (200, {"ok": True}))
        self.assertEqual(len(self.api_connections()), 1)
        self.assertEqual([url for _, url in self.api_connections()[0].calls],
                         ['/v1/me/player/queue', '/v1/me/player/currently-playing'])

    def test_connections_verify_certificates_without_strict_x509(self):
        widget._spotify_api_request("GET", "/me/player/queue")
        context = self.api_connections()[0].kwargs.get('context')
        self.assertIsInstance(context, ssl.SSLContext)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertFalse(context.verify_flags & ssl.VERIFY_X509_STRICT)

    def test_stale_connection_is_replaced_and_request_retried(self):
        widget._spotify_api_request("GET", "/me/player/queue")
        FakeConnection.fail_next = 1
        status, _ = widget._spotify_api_request("GET", "/me/player/queue")
        self.assertEqual(status, 200)
        self.assertEqual(len(self.api_connections()), 2)
        self.assertTrue(self.api_connections()[0].closed)
        self.assertEqual(len(self.api_connections()[1].calls), 1)


class SpotifySearchTests(unittest.TestCase):
    def setUp(self):
        self.settings = patch.multiple(widget, SPOTIFY_QUEUE_ON_REQUEST=True, SPOTIFY_DEVICE_ID='')
        self.settings.start()
        self.addCleanup(self.settings.stop)
        for target in (
            patch.object(widget, '_spotify_auth_ready', return_value=True),
            patch.object(widget, '_save_manual_spotify_queue_state_unlocked'),
        ):
            target.start()
            self.addCleanup(target.stop)
        widget.spotify_manual_queue_uris.clear()
        widget._invalidate_spotify_device_cache()
        self.calls = []

    def fake_api(self, search_results, queue_status=204):
        def api(method, path, query=None, retry_on_401=True, want_json=True):
            query = dict(query or {})
            self.calls.append((method, path, query))
            if path == "/search":
                return 200, {"tracks": {"items": search_results(query.get("q", ""))}}
            if path == "/me/player/devices":
                return 200, {"devices": [{"id": "dev1", "is_active": True}]}
            if path == "/me/player/queue":
                if callable(queue_status):
                    return queue_status(query), None
                return queue_status, None
            return 404, {}
        return api

    def count(self, path):
        return len([c for c in self.calls if c[1] == path])

    def test_search_stops_after_confident_match(self):
        api = self.fake_api(lambda q: [track("Song", "Artist", "spotify:track:1")])
        with patch.object(widget, '_spotify_api_request', side_effect=api):
            result = widget.queue_spotify_track_from_request("Song by Artist", requester="Viewer")
        self.assertTrue(result["ok"])
        self.assertEqual(result["track_uri"], "spotify:track:1")
        self.assertEqual(self.count("/search"), 1)

    def test_search_fans_out_when_first_query_is_not_confident(self):
        def results(q):
            if q.startswith('track:"'):
                return []
            return [track("Song (Live)", "Artist", "spotify:track:live", popularity=20)]
        api = self.fake_api(results)
        with patch.object(widget, '_spotify_api_request', side_effect=api):
            result = widget.queue_spotify_track_from_request("Song by Artist")
        self.assertTrue(result["ok"])
        self.assertEqual(result["track_uri"], "spotify:track:live")
        queries, _, _ = widget._spotify_search_queries("Song by Artist")
        self.assertEqual(self.count("/search"), min(6, len(queries)))

    def test_device_lookup_is_cached_across_requests(self):
        api = self.fake_api(lambda q: [track("Song", "Artist", "spotify:track:1")])
        with patch.object(widget, '_spotify_api_request', side_effect=api):
            first = widget.queue_spotify_track_from_request("Song by Artist")
            second = widget.queue_spotify_track_from_request("Song by Artist")
        self.assertEqual((first["device_id_used"], second["device_id_used"]), ("dev1", "dev1"))
        self.assertEqual(self.count("/me/player/devices"), 1)

    def test_failed_queue_add_with_cached_device_invalidates_cache(self):
        def queue_status(query):
            if query.get("device_id"):
                raise RuntimeError("Spotify API error (404) on /me/player/queue: Device not found")
            return 204
        api = self.fake_api(lambda q: [track("Song", "Artist", "spotify:track:1")], queue_status=queue_status)
        with patch.object(widget, '_spotify_api_request', side_effect=api):
            first = widget.queue_spotify_track_from_request("Song by Artist")
            self.assertTrue(first["ok"])
            self.assertEqual(first["device_id_used"], "")
            widget.queue_spotify_track_from_request("Song by Artist")
        self.assertEqual(self.count("/me/player/devices"), 2)


class AlbumArtTests(unittest.TestCase):
    def setUp(self):
        widget._reset_album_art_cache()
        auth = patch.object(widget, '_spotify_auth_ready', return_value=True)
        auth.start()
        self.addCleanup(auth.stop)
        self.calls = []

    def api_returning(self, items):
        def api(method, path, query=None, retry_on_401=True, want_json=True):
            self.calls.append(path)
            return 200, {"tracks": {"items": items}}
        return api

    def test_album_art_lookup_is_cached_per_track(self):
        with patch.object(widget, '_spotify_api_request', side_effect=self.api_returning([track("Song", "Artist", "spotify:track:1")])):
            self.assertEqual(widget._spotify_find_album_art_for_track("Song", "Artist"), "https://img.example/1")
            self.assertEqual(widget._spotify_find_album_art_for_track("Song", "Artist"), "https://img.example/1")
        self.assertEqual(self.calls, ["/search"])

    def test_missing_album_art_is_not_retried_every_poll(self):
        with patch.object(widget, '_spotify_api_request', side_effect=self.api_returning([])):
            self.assertEqual(widget._spotify_find_album_art_for_track("Song", "Artist"), "")
            self.assertEqual(widget._spotify_find_album_art_for_track("Song", "Artist"), "")
        self.assertEqual(self.calls, ["/search"])

    def test_poller_looks_up_album_art_without_holding_state_lock(self):
        acquired = []

        def art_lookup(title, artist):
            def probe():
                got = widget.state_lock.acquire(timeout=0.5)
                acquired.append(got)
                if got:
                    widget.state_lock.release()
            probe_thread = threading.Thread(target=probe)
            probe_thread.start()
            probe_thread.join()
            return "https://img.example/now"

        now_snapshot = {"available": True, "title": "Song", "artist": "Artist", "album_art": "",
                        "elapsed_sec": 1, "duration_sec": 100, "playing": True}
        with patch.object(widget, 'fetch_spotify_queue_state', return_value=([], "")), \
                patch.object(widget, 'fetch_spotify_now_playing_state', return_value=(now_snapshot, "")), \
                patch.object(widget, '_spotify_find_album_art_for_track', side_effect=art_lookup), \
                patch.object(widget.socketio, 'emit'):
            widget._spotify_poll_once()
        self.assertEqual(acquired, [True])
        self.assertEqual(widget.now_playing_state["album_art"], "https://img.example/now")


class OverlayTransportTests(unittest.TestCase):
    def test_overlays_try_websocket_before_long_polling(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for name in ('index.html', 'queue_widget.html'):
            with self.subTest(file=name):
                with open(os.path.join(root, name), encoding='utf-8') as handle:
                    source = handle.read()
                self.assertIn("transports: ['websocket', 'polling']", source)
                self.assertNotIn("transports: ['polling', 'websocket']", source)


class ManualQueueStatePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, 'state.json')
        settings = patch.multiple(widget, SPOTIFY_MANUAL_QUEUE_STATE_FILE=self.path)
        settings.start()
        self.addCleanup(settings.stop)
        widget.spotify_manual_queue_uris.clear()
        widget.spotify_manual_queue_uris.append(
            {"uri": "spotify:track:abc", "key": "", "title": "Song", "artist": "Artist", "requester": "Viewer"})
        widget.spotify_manual_queue_last_saved = ""

    def test_state_file_is_written_off_the_calling_thread(self):
        writer_threads = []
        real_write = widget._write_manual_queue_state_file

        def record(path, payload):
            writer_threads.append(threading.current_thread())
            real_write(path, payload)

        with patch.object(widget, '_write_manual_queue_state_file', side_effect=record):
            with widget.state_lock:
                widget._save_manual_spotify_queue_state_unlocked(force=True)
            self.assertTrue(widget.wait_for_background_writes(timeout=5))
        self.assertEqual(len(writer_threads), 1)
        self.assertIsNot(writer_threads[0], threading.current_thread())
        with open(self.path, encoding='utf-8') as handle:
            saved = json.load(handle)
        self.assertEqual(saved["uris"], ["spotify:track:abc"])
        self.assertEqual(saved["entries"][0]["requester"], "Viewer")


if __name__ == '__main__':
    unittest.main()
