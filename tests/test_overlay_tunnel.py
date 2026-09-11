import io
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, call, patch
import urllib.error

import _launch_overlay_tunnel as tunnel


class OverlayTunnelTests(unittest.TestCase):
    def setUp(self):
        self.origin = 'https://example-overlay-test.trycloudflare.com'
        self.urls = tunnel.overlay_urls(self.origin)
        output_patch = patch('builtins.print')
        self.output = output_patch.start()
        self.addCleanup(output_patch.stop)

    def test_two_overlay_paths_share_one_origin(self):
        self.assertEqual(self.urls, [
            ('Skip Overlay', self.origin + '/'),
            ('Queue Overlay', self.origin + '/queue_widget'),
        ])

    def test_only_exact_cloudflare_https_origins_are_detected(self):
        match = tunnel.TUNNEL_URL_PATTERN.search('| ' + self.origin + ' |')
        self.assertEqual(match.group(0), self.origin)
        for invalid in (
            'http://example-overlay-test.trycloudflare.com',
            self.origin + '.untrusted.example',
            self.origin + '@untrusted.example',
            'https://-invalid.trycloudflare.com',
            'https://127.0.0.1',
        ):
            with self.subTest(url=invalid):
                self.assertIsNone(tunnel.TUNNEL_URL_PATTERN.search(invalid))

    def test_readiness_checks_head_requests(self):
        with patch.object(tunnel.urllib.request, 'urlopen') as open_url:
            open_url.return_value.__enter__.return_value.status = 200
            self.assertTrue(tunnel.url_is_ready(self.origin + '/'))
            request = open_url.call_args.args[0]
            self.assertEqual(request.get_method(), 'HEAD')
            self.assertEqual(open_url.call_args.kwargs['timeout'], 3)
            open_url.return_value.__enter__.return_value.status = 503
            self.assertFalse(tunnel.url_is_ready(self.origin + '/'))

    def test_readiness_errors_are_retryable(self):
        for error in (urllib.error.URLError('not ready'), TimeoutError('timed out')):
            with patch.object(tunnel.urllib.request, 'urlopen', side_effect=error):
                self.assertFalse(tunnel.url_is_ready(self.origin + '/'))

    def test_both_tabs_open_once_after_both_routes_are_ready(self):
        stopped = MagicMock()
        stopped.is_set.return_value = False
        stopped.wait.return_value = False
        with patch.object(tunnel, 'url_is_ready', side_effect=[True, False, True, True]) as ready:
            with patch.object(tunnel.webbrowser, 'open_new_tab', return_value=True) as open_tab:
                tunnel.open_overlays_when_ready(self.urls, stopped)
        self.assertEqual(ready.call_count, 4)
        self.assertEqual(open_tab.call_args_list, [call(self.origin + '/'), call(self.origin + '/queue_widget')])
        stopped.wait.assert_called_once_with(1)

    def test_readiness_timeout_does_not_open_broken_pages(self):
        with patch.object(tunnel.webbrowser, 'open_new_tab') as open_tab:
            tunnel.open_overlays_when_ready(self.urls, threading.Event(), timeout=0)
        open_tab.assert_not_called()
        self.assertIn('not reachable yet', self.output.call_args.args[0])

    def test_shutdown_cancels_browser_opening(self):
        stopped = threading.Event()
        stopped.set()
        with patch.object(tunnel.webbrowser, 'open_new_tab') as open_tab:
            tunnel.open_overlays_when_ready(self.urls, stopped)
        open_tab.assert_not_called()

    def test_browser_failure_does_not_skip_second_overlay(self):
        with patch.object(tunnel, 'url_is_ready', return_value=True):
            with patch.object(tunnel.webbrowser, 'open_new_tab', side_effect=[OSError('no browser'), True]) as open_tab:
                tunnel.open_overlays_when_ready(self.urls, threading.Event())
        self.assertEqual(open_tab.call_count, 2)

    def fake_process(self, log):
        process = MagicMock()
        process.stdout = io.StringIO(log)
        process.wait.return_value = 0
        process.poll.return_value = 0
        return process

    def test_launcher_starts_one_tunnel_and_saves_both_urls(self):
        process = self.fake_process(self.origin + '\nRegistered tunnel connection\n' + self.origin + '\n')
        with tempfile.TemporaryDirectory(prefix='overlay-tunnel-test-') as directory:
            urls_file = Path(directory) / 'last_tunnel_urls.txt'
            with patch.object(tunnel.subprocess, 'Popen', return_value=process) as start_process:
                with patch.object(tunnel.threading, 'Thread') as worker:
                    self.assertEqual(tunnel.run_tunnel(5050, urls_file), 0)
            contents = urls_file.read_text(encoding='utf-8')
        start_process.assert_called_once()
        self.assertEqual(start_process.call_args.args[0], ['cloudflared', 'tunnel', '--url', 'http://127.0.0.1:5050'])
        if os.name == 'nt':
            self.assertEqual(start_process.call_args.kwargs['creationflags'], subprocess.CREATE_NO_WINDOW)
        worker.assert_called_once()
        worker.return_value.start.assert_called_once()
        worker.return_value.join.assert_called_once()
        self.assertIn('Skip Overlay: ' + self.origin + '/', contents)
        self.assertIn('Queue Overlay: ' + self.origin + '/queue_widget', contents)
        self.assertTrue(process.stdout.closed)

    def test_auto_open_can_be_disabled_without_disabling_tunnel(self):
        process = self.fake_process(self.origin + '\n')
        with tempfile.TemporaryDirectory(prefix='overlay-tunnel-test-') as directory:
            with patch.object(tunnel.subprocess, 'Popen', return_value=process):
                with patch.object(tunnel.threading, 'Thread') as worker:
                    result = tunnel.run_tunnel(5000, Path(directory) / 'urls.txt', auto_open=False)
        self.assertEqual(result, 0)
        worker.assert_not_called()

    def test_missing_url_does_not_leave_stale_saved_links(self):
        process = self.fake_process('Tunnel could not connect\n')
        with tempfile.TemporaryDirectory(prefix='overlay-tunnel-test-') as directory:
            urls_file = Path(directory) / 'urls.txt'
            urls_file.write_text('old URL', encoding='utf-8')
            with patch.object(tunnel.subprocess, 'Popen', return_value=process):
                self.assertEqual(tunnel.run_tunnel(5000, urls_file), 1)
            self.assertNotIn('old URL', urls_file.read_text(encoding='utf-8'))

    def test_missing_cloudflared_reports_failure(self):
        with tempfile.TemporaryDirectory(prefix='overlay-tunnel-test-') as directory:
            with patch.object(tunnel.subprocess, 'Popen', side_effect=FileNotFoundError('cloudflared')):
                self.assertEqual(tunnel.run_tunnel(5000, Path(directory) / 'urls.txt'), 1)

    def test_shutdown_stops_only_the_owned_process(self):
        process = MagicMock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired('cloudflared', 5), 0]
        tunnel.stop_tunnel(process)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        self.assertEqual(process.wait.call_count, 2)

    def test_tunnel_launcher_uses_the_shared_helper(self):
        # start_dual_overlay.bat is the local-only launcher and intentionally starts no tunnel.
        root = Path(__file__).resolve().parents[1]
        source = (root / 'start_with_tunnel.bat').read_text(encoding='utf-8')
        self.assertIn('python "%~dp0_launch_overlay_tunnel.py" --port "%PORT%"', source)
        self.assertLess(source.index(':server_ready'), source.index('python "%~dp0_launch_overlay_tunnel.py"'))
        local_source = (root / 'start_dual_overlay.bat').read_text(encoding='utf-8')
        self.assertNotIn('_launch_overlay_tunnel.py', local_source)


if __name__ == '__main__':
    unittest.main()
