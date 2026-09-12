"""Graphical entry point for LiveWidget.exe."""

import argparse
import json
import os
from pathlib import Path
import queue
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.parse
import webbrowser

from desktop_runtime import (
    WidgetProcess, cloudflared_path, load_settings, protect_secret,
    run_server, save_settings, user_data_dir,
)
from spotify_app_config import PUBLIC_CLIENT_ID


APP_NAME = 'Live Widget'


class DesktopApp:
    def __init__(self, root, directory):
        import tkinter as tk
        from tkinter import messagebox

        self.root, self.directory = root, directory
        self.messagebox = messagebox
        self.process = WidgetProcess(directory)
        self.events = queue.Queue()
        self.busy = False
        self.closing = False
        self.running = False
        self.oauth_cancelled = threading.Event()
        self.oauth_busy = False
        self.settings = load_settings(directory)
        self.variables = {name: (tk.BooleanVar(value=value) if isinstance(value, bool) else tk.StringVar(value=value))
                          for name, value in self.settings.items()}
        from desktop_ui import LauncherView

        self.saved_settings = dict(self.settings)
        self.view = LauncherView(self)
        root.protocol('WM_DELETE_WINDOW', self.close)
        for variable in self.variables.values():
            variable.trace_add('write', self.settings_changed)
        self.tick_after = root.after(250, self.tick)

    def copy(self, value, label='Link'):
        if not value:
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(value)
            self.view.notify(label + (' copied. Keep it private.' if label == 'Control password' else ' copied to clipboard.'))
        except Exception:
            self.view.show_error('Could not copy to the clipboard. Please try again.')

    def open_url(self, url):
        if not url:
            return
        try:
            if not webbrowser.open(url):
                raise OSError('No default browser')
        except Exception:
            self.view.show_error('Could not open your browser. Copy the link and open it manually.')

    def open_data_folder(self):
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            os.startfile(str(self.directory))
        except OSError:
            self.view.show_error('Could not open the settings folder. Its location is shown under Preferences.')

    def settings_changed(self, *arguments):
        self.view.refresh_settings()

    def values(self):
        return {name: variable.get() for name, variable in self.variables.items()}

    def save(self):
        if self.process.server is not None or self.oauth_busy or self.busy:
            return False
        try:
            save_settings(self.directory, self.values())
            self.saved_settings = self.values()
            self.view.refresh_settings()
            self.view.notify('Settings saved for your Windows account.')
            return True
        except (OSError, ValueError) as error:
            self.view.show_error(str(error))
            return False

    def set_active(self, active):
        self.view.set_active(active or self.oauth_busy)

    def start(self):
        if self.oauth_busy or self.busy or self.process.server is not None:
            return
        self.view.clear_notice()
        try:
            self.process.start(self.values())
        except (OSError, ValueError, RuntimeError) as error:
            self.view.show_error(str(error))
            return
        self.saved_settings = dict(self.process.settings)
        for name, value in self.saved_settings.items():
            self.variables[name].set(value)
        self.running = False
        self.set_active(True)
        self.view.mask_secrets()
        self.view.set_session('starting')
        self.status.set('Starting the local server. Your links will appear when it is ready.')

    def stop(self):
        if self.busy or self.process.server is None:
            return
        self.busy = True
        self.set_active(True)
        self.view.set_session('stopping')
        self.status.set('Stopping the widget and its tunnel...')
        self.view.links_ready(False)
        for variable in self.urls.values():
            variable.set('')

        def worker():
            try:
                self.process.stop()
                self.events.put(('stopped', ''))
            except Exception as error:
                self.events.put(('stopped', str(error)))

        threading.Thread(target=worker, daemon=True).start()

    def close(self):
        if self.closing:
            return
        if self.oauth_busy:
            if not self.messagebox.askyesno('Cancel Spotify sign-in?',
                                           'Closing cancels the current sign-in and discards unsaved settings.\n\nExit Live Widget?',
                                           parent=self.root, default='no'):
                return
        if self.process.server is not None and not self.busy:
            if not self.messagebox.askyesno('Stop your widget?', 'Closing Live Widget stops its overlays and public tunnel.\n\nStop the session and exit?', parent=self.root, default='no'):
                return
        if self.process.server is None and not self.oauth_busy and self.values() != self.saved_settings:
            answer = self.messagebox.askyesnocancel('Save your changes?', 'Save your updated settings before closing?', parent=self.root)
            if answer is None or (answer and not self.save()):
                return
        self.closing = True
        self.oauth_cancelled.set()
        if self.process.server is not None or self.busy:
            self.stop()
        else:
            self.destroy()

    def destroy(self):
        self.oauth_cancelled.set()
        for callback in (self.tick_after, self.view.notice_after, self.view.scroll_after):
            if callback:
                self.root.after_cancel(callback)
        self.view.progress.stop()
        self.view.oauth_progress.stop()
        self.root.destroy()

    def cancel_spotify(self):
        if self.oauth_busy:
            self.oauth_cancelled.set()
            self.view.cancel_button.configure(state='disabled')
            self.spotify_status.set('Cancelling sign-in...')

    def connect_spotify(self):
        from spotify_oauth_helper import AUTH_URL, DEFAULT_REDIRECT_URI, SCOPES, CallbackServer, create_pkce_pair, _exchange_code_for_tokens

        if self.oauth_busy or self.busy or self.process.server is not None:
            return
        public_client_id = PUBLIC_CLIENT_ID
        client_id = public_client_id or self.variables['SPOTIFY_CLIENT_ID'].get().strip()
        client_secret = '' if public_client_id else self.variables['SPOTIFY_CLIENT_SECRET'].get().strip()
        if not client_id or (not public_client_id and not client_secret):
            self.view.show_error('Enter your own Spotify client ID and client secret first.',
                                 field='SPOTIFY_CLIENT_ID' if not client_id else 'SPOTIFY_CLIENT_SECRET')
            return
        self.oauth_busy = True
        self.oauth_cancelled.clear()
        self.view.clear_notice()
        self.set_active(True)
        self.view.oauth_pending(True)
        self.spotify_status.set('Waiting for Spotify authorization in your browser (up to 3 minutes)...')

        def worker():
            callback = None
            result = ('spotify_cancelled', '')
            try:
                state = secrets.token_urlsafe(24)
                code_verifier, code_challenge = create_pkce_pair() if public_client_id else ('', '')
                callback = CallbackServer('127.0.0.1', 8888, state)
                callback.start()
                parameters = {'client_id': client_id, 'response_type': 'code', 'redirect_uri': DEFAULT_REDIRECT_URI,
                              'scope': SCOPES, 'state': state, 'show_dialog': 'true'}
                if code_challenge:
                    parameters.update({'code_challenge_method': 'S256', 'code_challenge': code_challenge})
                if not webbrowser.open(AUTH_URL + '?' + urllib.parse.urlencode(parameters)):
                    raise RuntimeError('Could not open the browser. Check your default browser and try again.')
                deadline = time.monotonic() + 180
                while not callback.done.wait(0.3):
                    if self.oauth_cancelled.is_set():
                        return
                    if time.monotonic() > deadline:
                        raise RuntimeError('Spotify authorization timed out. Please try again.')
                if callback.error or not callback.code:
                    raise RuntimeError('Spotify did not authorize this account. Check your app settings and account access.')
                tokens = _exchange_code_for_tokens(
                    client_id, client_secret, callback.code, DEFAULT_REDIRECT_URI,
                    code_verifier=code_verifier or None,
                )
                if self.oauth_cancelled.is_set():
                    return
                if not tokens.get('refresh_token'):
                    raise RuntimeError('Spotify did not return a refresh token. Please reconnect.')
                result = ('spotify', (
                    '' if public_client_id else client_id,
                    '' if public_client_id else client_secret,
                    tokens['refresh_token'],
                ))
            except Exception as error:
                result = ('spotify_error', str(error))
            finally:
                if callback:
                    callback.stop()
                self.events.put(result)

        threading.Thread(target=worker, daemon=True).start()

    def update_urls(self, public=''):
        origin = public or self.process.origin
        self.urls['Skip overlay'].set(origin + '/')
        self.urls['Queue overlay'].set(origin + '/queue_widget')
        self.urls['Control panel'].set(self.process.origin + '/control')
        self.view.links_ready(True, public=bool(public))

    def tick(self):
        while not self.events.empty():
            kind, value = self.events.get_nowait()
            if kind == 'stopped':
                self.busy = self.running = False
                if self.closing:
                    self.destroy()
                    return
                self.set_active(False)
                self.view.set_session('stopped')
                self.status.set('Stopped.' if not value else 'Stop failed: ' + value)
                if value:
                    self.view.show_error('Could not finish stopping: ' + value)
            else:
                self.oauth_busy = False
                self.set_active(self.process.server is not None)
                self.view.oauth_pending(False)
                if kind == 'spotify':
                    for name, credential in zip(('SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET', 'SPOTIFY_REFRESH_TOKEN'), value):
                        self.variables[name].set(credential)
                    if self.save():
                        self.spotify_status.set('Authorization saved. Start a live chat mode to enable Spotify requests.')
                    else:
                        self.spotify_status.set('Authorized, but settings could not be saved. Try Save settings again.')
                elif kind == 'spotify_cancelled':
                    self.spotify_status.set('Sign-in cancelled. Your existing credentials were not changed.')
                else:
                    self.spotify_status.set(value)
                    self.view.notify('Spotify sign-in failed. ' + value, error=True)
        if self.process.server is not None and not self.busy:
            try:
                if self.process.server.poll() is not None:
                    raise RuntimeError('The widget exited. Open server.log in the logs folder for details.')
                if not self.running:
                    if self.process.ready():
                        self.running = True
                        self.view.set_session('running')
                        self.update_urls()
                        self.status.set('Preview is running. No live chat or playback connections.' if self.variables['CHAT_SOURCE'].get() == 'preview'
                                        else 'Local server ready. Check server.log for live chat connection status.')
                        self.view.show_page('overlays')
                        if self.process.settings['AUTO_OPEN']:
                            self.open_url(self.process.origin + '/control')
                        if self.process.settings['PUBLIC_TUNNEL']:
                            self.process.start_tunnel()
                            self.status.set('Local widget running. Waiting for Cloudflare HTTPS links...')
                    elif time.monotonic() - self.process.started_at > 60:
                        raise RuntimeError('Startup timed out. Open server.log in the logs folder for details.')
                if self.process.tunnel is not None:
                    if self.process.tunnel.poll() is not None:
                        self.process.tunnel = None
                        if self.process.tunnel_log:
                            self.process.tunnel_log.close()
                            self.process.tunnel_log = None
                        self.update_urls()
                        (self.directory / 'last_tunnel_urls.txt').write_text('Tunnel exited. Restart to get new HTTPS URLs.\n', encoding='utf-8')
                        self.status.set('Cloudflare exited; local overlays still work. Check cloudflared.log, then Stop / Start to retry.')
                    elif self.process.read_tunnel_origin():
                        self.update_urls(self.process.public_origin)
                        self.status.set('Widget running. HTTPS links assigned; Cloudflare may take a minute to connect.')
            except Exception as error:
                self.stop()
                self.view.show_error(str(error))
        self.tick_after = self.root.after(500, self.tick)


def self_test(output):
    report = {}
    try:
        os.environ.update({'ALLOWED_ORIGINS': '', 'CONTROL_PASSWORD': 'self-test-password-only'})
        import tkinter as tk
        import live_widget as widget
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager

        with tempfile.TemporaryDirectory(prefix='widget-gui-self-test-') as temporary:
            root = tk.Tk()
            root.withdraw()
            desktop = DesktopApp(root, Path(temporary))
            for page in desktop.view.pages:
                desktop.view.show_page(page)
                root.update_idletasks()
            desktop.destroy()
        report['gui'] = True
        report['windows_media'] = GlobalSystemMediaTransportControlsSessionManager is not None
        client = widget.app.test_client()
        report['pages'] = {path: client.get(path).status_code for path in ('/', '/queue_widget', '/control')}
        connection = widget.socketio.test_client(widget.app)
        report['socket_connected'] = connection.is_connected()
        report['control_auth'] = connection.emit('mod_auth', {'password': 'self-test-password-only'}, callback=True)
        connection.disconnect()
        report['data_protection'] = protect_secret(protect_secret(b'self-test'), decrypt=True) == b'self-test'
        report['cloudflare'] = subprocess.check_output([cloudflared_path(), '--version'], text=True,
                                                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=20).strip()
        report['ok'] = all(code == 200 for code in report['pages'].values()) and report['socket_connected'] and report['control_auth'].get('success') and report['data_protection']
    except Exception:
        report['ok'] = False
        report['error'] = traceback.format_exc()
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return 0 if report['ok'] else 1


def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument('--server', action='store_true')
    parser.add_argument('--data-dir', type=Path, default=user_data_dir())
    parser.add_argument('--session', default='')
    parser.add_argument('--parent-pid', type=int, default=0)
    parser.add_argument('--self-test', type=Path)
    arguments = parser.parse_args()
    if arguments.self_test:
        return self_test(arguments.self_test)
    if arguments.server:
        if not arguments.session or not arguments.session.isalnum():
            parser.error('--server requires an alphanumeric --session')
        return run_server(arguments)
    import tkinter as tk
    from tkinter import messagebox

    directory = arguments.data_dir.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    sys.stdout = sys.stderr = (directory / 'launcher.log').open('w', encoding='utf-8', buffering=1)
    root = tk.Tk()
    try:
        DesktopApp(root, directory)
        root.mainloop()
        return 0
    except Exception as error:
        traceback.print_exc()
        root.withdraw()
        messagebox.showerror(APP_NAME, f'Could not open Live Widget: {error}\n\nSettings folder: {directory}')
        root.destroy()
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
