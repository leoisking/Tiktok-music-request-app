import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

import desktop_runtime as runtime


class DesktopSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='widget-desktop-test-')
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.settings = runtime.load_settings(self.directory)

    def test_first_run_has_no_personal_accounts(self):
        self.assertEqual(self.settings['CHAT_SOURCE'], 'preview')
        self.assertFalse(self.settings['PUBLIC_TUNNEL'])
        for name in ('TIKTOK_USER', 'TWITCH_CHANNEL', 'SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET', 'SPOTIFY_REFRESH_TOKEN'):
            self.assertEqual(self.settings[name], '')
        self.assertGreaterEqual(len(self.settings['CONTROL_PASSWORD']), 24)
        self.assertNotEqual(self.settings['CONTROL_PASSWORD'], runtime.load_settings(self.directory)['CONTROL_PASSWORD'])

    @unittest.skipUnless(os.name == 'nt', 'Windows data protection')
    def test_secrets_round_trip_without_plaintext_on_disk(self):
        for name in runtime.SECRET_FIELDS:
            self.settings[name] = 'test-private-\U0001f512-' + name
        runtime.save_settings(self.directory, self.settings)
        contents = (self.directory / 'settings.json').read_text(encoding='utf-8')
        for name in runtime.SECRET_FIELDS:
            self.assertNotIn(self.settings[name], contents)
        self.assertEqual(runtime.load_settings(self.directory), self.settings)
        self.assertFalse((self.directory / 'settings.json.tmp').exists())

    def test_invalid_settings_fail_instead_of_overwriting(self):
        path = self.directory / 'settings.json'
        for payload in ('[]', '{broken', '{"version": 9}', '{"version": 1, "settings": []}'):
            with self.subTest(payload=payload):
                path.write_text(payload, encoding='utf-8')
                with self.assertRaises(ValueError):
                    runtime.load_settings(self.directory)
                self.assertEqual(path.read_text(encoding='utf-8'), payload)

    def test_preview_requires_no_external_accounts(self):
        self.assertEqual(runtime.validate_settings(self.settings)['CHAT_SOURCE'], 'preview')

    def test_live_modes_require_their_channel(self):
        for source in ('tiktok', 'twitch', 'both'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                runtime.validate_settings({**self.settings, 'CHAT_SOURCE': source})

    def test_usernames_are_normalized_without_mutating_input(self):
        settings = {**self.settings, 'CHAT_SOURCE': 'both', 'TIKTOK_USER': ' @sample ', 'TWITCH_CHANNEL': ' #EXAMPLE '}
        result = runtime.validate_settings(settings)
        self.assertEqual(result['TIKTOK_USER'], 'sample')
        self.assertEqual(result['TWITCH_CHANNEL'], 'example')
        self.assertEqual(settings['TIKTOK_USER'], ' @sample ')

    def test_invalid_ports_thresholds_and_passwords(self):
        for name, values in {
            'PORT': ('0', '-1', '65536', '5000 & exit', ''),
            'SKIP_THRESHOLD': ('0', 'one', '10001'),
            'CONTROL_PASSWORD': ('', 'short', ' ' * 16, 'YourSecurePassword', 'your_secure_pass'),
            'CHAT_SOURCE': ('unknown',),
        }.items():
            for value in values:
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    runtime.validate_settings({**self.settings, name: value})

    def test_partial_spotify_configuration_is_rejected_for_live_mode(self):
        with self.assertRaises(ValueError):
            runtime.validate_settings({**self.settings, 'CHAT_SOURCE': 'twitch', 'TWITCH_CHANNEL': 'sample', 'SPOTIFY_CLIENT_ID': 'test'})

    def test_public_spotify_configuration_allows_refresh_token_only(self):
        settings = {**self.settings, 'CHAT_SOURCE': 'twitch', 'TWITCH_CHANNEL': 'sample',
                    'SPOTIFY_REFRESH_TOKEN': 'refresh-token'}
        with patch.object(runtime, 'PUBLIC_CLIENT_ID', 'public-client-id'):
            result = runtime.validate_settings(settings)
            environment = runtime.server_environment(result, self.directory)
        self.assertEqual(environment['SPOTIFY_CLIENT_ID'], 'public-client-id')
        self.assertEqual(environment['SPOTIFY_CLIENT_SECRET'], '')

    def test_environment_does_not_inherit_accounts_or_insecure_origin(self):
        with patch.dict(os.environ, {'SPOTIFY_REFRESH_TOKEN': 'do-not-use', 'TWITCH_OAUTH_TOKEN': 'do-not-use',
                                     'TIKTOK_USER': 'do-not-use', 'ALLOWED_ORIGINS': '*', 'HOST': '0.0.0.0'}):
            environment = runtime.server_environment(self.settings, self.directory)
        self.assertEqual(environment['SPOTIFY_REFRESH_TOKEN'], '')
        self.assertEqual(environment['TWITCH_OAUTH_TOKEN'], '')
        self.assertEqual(environment['TIKTOK_USER'], '')
        self.assertEqual(environment['HOST'], '127.0.0.1')
        self.assertEqual(environment['ALLOWED_ORIGINS'], '')
        self.assertEqual(environment['SPOTIFY_QUEUE_ON_REQUEST'], '0')
        self.assertEqual(environment['SPOTIFY_MANUAL_QUEUE_STATE_FILE'], str(self.directory / 'spotify_manual_queue_state.json'))

    def test_frozen_worker_runs_executable_not_python_script(self):
        with patch.object(sys, 'frozen', True, create=True):
            command = runtime.worker_command(self.directory, 'session')
        self.assertEqual(command[:2], [sys.executable, '--server'])
        self.assertNotIn('live_widget.py', command)
        self.assertIn(str(self.directory), command)

    def test_source_worker_runs_desktop_entry_point(self):
        command = runtime.worker_command(self.directory, 'session')
        self.assertEqual(Path(command[1]).name, 'desktop_launcher.py')

    def test_bundled_cloudflare_precedes_path(self):
        binary = self.directory / 'cloudflared.exe'
        binary.touch()
        with patch.object(runtime, 'resource_path', return_value=binary), patch.object(runtime.shutil, 'which', return_value='other.exe'):
            self.assertEqual(runtime.cloudflared_path(), str(binary))

    def test_occupied_port_is_not_killed_or_reused(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            port = listener.getsockname()[1]
            with patch.object(runtime.subprocess, 'Popen') as spawn, self.assertRaisesRegex(ValueError, 'already in use'):
                runtime.WidgetProcess(self.directory).start({**self.settings, 'PORT': str(port)})
            spawn.assert_not_called()
            self.assertEqual(listener.getsockname()[1], port)

    def test_tunnel_log_handles_partial_lines(self):
        process = runtime.WidgetProcess(self.directory)
        process.tunnel = MagicMock()
        path = self.directory / 'cloudflared.log'
        path.write_bytes(b'https://example-overlay.trycloud')
        self.assertEqual(process.read_tunnel_origin(), '')
        with path.open('ab') as log:
            log.write(b'flare.com |\n')
        origin = process.read_tunnel_origin()
        self.assertEqual(origin, 'https://example-overlay.trycloudflare.com')
        saved = (self.directory / 'last_tunnel_urls.txt').read_text(encoding='utf-8')
        self.assertIn(origin + '/queue_widget', saved)
        self.assertNotIn('/control', saved)

    def test_stop_only_touches_owned_processes(self):
        process = runtime.WidgetProcess(self.directory)
        process.session = 'testsession'
        process.server = MagicMock()
        process.tunnel = MagicMock()
        tunnel = process.tunnel
        server = process.server
        with patch.object(runtime, 'stop_tunnel') as stop:
            process.stop()
        stop.assert_called_once_with(tunnel)
        server.wait.assert_called_once_with(timeout=8)
        self.assertIsNone(process.server)
        self.assertIsNone(process.tunnel)
        self.assertFalse((self.directory / 'testsession.stop').exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows desktop integration')
    def test_preview_worker_starts_serves_assets_and_stops(self):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        settings = {**self.settings, 'PORT': str(port), 'AUTO_OPEN': False}
        process = runtime.WidgetProcess(self.directory)
        try:
            process.start(settings)
            deadline = time.monotonic() + 35
            while not process.ready() and time.monotonic() < deadline:
                time.sleep(0.2)
            diagnostic = (self.directory / 'server.log').read_text(encoding='utf-8') if (self.directory / 'server.log').exists() else 'No server log'
            self.assertTrue(process.ready(), diagnostic)
            for path in ('/', '/queue_widget', '/control'):
                with runtime.urllib.request.urlopen(process.origin + path, timeout=3) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn(b'<html', response.read().lower())
            self.assertEqual(json.loads((self.directory / 'settings.json').read_text(encoding='utf-8'))['settings']['CHAT_SOURCE'], 'preview')
        finally:
            process.stop()
        self.assertTrue(runtime.port_is_available(port))


if __name__ == '__main__':
    unittest.main()
