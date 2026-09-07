"""Configuration and process management for the Windows desktop launcher."""

import asyncio
import base64
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.request

from _launch_overlay_tunnel import TUNNEL_URL_PATTERN, stop_tunnel


SECRET_FIELDS = ('CONTROL_PASSWORD', 'SPOTIFY_CLIENT_SECRET', 'SPOTIFY_REFRESH_TOKEN', 'TWITCH_OAUTH_TOKEN')
DEFAULTS = {
    'CHAT_SOURCE': 'preview', 'TIKTOK_USER': '', 'TWITCH_CHANNEL': '',
    'TWITCH_BOT_USERNAME': '', 'TWITCH_OAUTH_TOKEN': '', 'MOD_LIST': '',
    'CONTROL_PASSWORD': '', 'PORT': '5000', 'SKIP_THRESHOLD': '10',
    'ADAPTIVE_SKIP_THRESHOLD_ENABLED': True, 'PUBLIC_TUNNEL': False,
    'SPOTIFY_CLIENT_ID': '', 'SPOTIFY_CLIENT_SECRET': '', 'SPOTIFY_REFRESH_TOKEN': '',
    'SPOTIFY_DEVICE_ID': '', 'AUTO_OPEN': True,
}


def resource_path(name):
    return Path(__file__).resolve().parent / name


def user_data_dir():
    return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'LiveWidget'


def protect_secret(payload, decrypt=False):
    if os.name != 'nt':
        raise OSError('Saving credentials requires Windows data protection.')

    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]

    buffer = ctypes.create_string_buffer(payload)
    source = Blob(len(payload), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    result = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    operation = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    operation.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                          ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    operation.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if not operation(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        kernel.LocalFree(result.data)


def load_settings(directory):
    settings = dict(DEFAULTS)
    path = directory / 'settings.json'
    if not path.exists():
        settings['CONTROL_PASSWORD'] = secrets.token_urlsafe(24)
        return settings
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict) or payload.get('version') != 1:
        raise ValueError('Unsupported settings file. Move settings.json aside to reset it.')
    public = payload.get('settings')
    if not isinstance(public, dict):
        raise ValueError('Invalid settings file.')
    for name, default in DEFAULTS.items():
        if name not in SECRET_FIELDS and name in public:
            if type(public[name]) is not type(default):
                raise ValueError(f'Invalid setting: {name}')
            settings[name] = public[name]
    encrypted = base64.b64decode(payload['protected_secrets'], validate=True)
    private = json.loads(protect_secret(encrypted, decrypt=True).decode('utf-8'))
    if not isinstance(private, dict) or any(not isinstance(value, str) for value in private.values()):
        raise ValueError('Invalid protected settings.')
    settings.update({name: private.get(name, '') for name in SECRET_FIELDS})
    return settings


def save_settings(directory, settings):
    private = {name: settings[name] for name in SECRET_FIELDS}
    payload = {
        'version': 1,
        'settings': {name: settings[name] for name in DEFAULTS if name not in SECRET_FIELDS},
        'protected_secrets': base64.b64encode(protect_secret(json.dumps(private).encode('utf-8'))).decode('ascii'),
    }
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / 'settings.json.tmp'
    temporary.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    temporary.replace(directory / 'settings.json')


def validate_settings(settings):
    settings = dict(settings)
    source = settings['CHAT_SOURCE']
    if source not in ('preview', 'tiktok', 'twitch', 'both'):
        raise ValueError('Choose preview, tiktok, twitch, or both.')
    settings['TIKTOK_USER'] = settings['TIKTOK_USER'].strip().lstrip('@')
    settings['TWITCH_CHANNEL'] = settings['TWITCH_CHANNEL'].strip().lstrip('#').lower()
    if source in ('tiktok', 'both') and not settings['TIKTOK_USER']:
        raise ValueError('Enter your TikTok username.')
    if source in ('twitch', 'both') and not settings['TWITCH_CHANNEL']:
        raise ValueError('Enter your Twitch channel.')
    for name, limit in (('PORT', 65535), ('SKIP_THRESHOLD', 10000)):
        try:
            number = int(settings[name])
        except (ValueError, TypeError):
            raise ValueError(f'{name} must be a whole number.') from None
        if not 1 <= number <= limit:
            raise ValueError(f'{name} must be between 1 and {limit}.')
        settings[name] = str(number)
    password = settings['CONTROL_PASSWORD']
    if len(password) < 12 or password.isspace() or password in ('YourSecurePassword', 'your_secure_pass'):
        raise ValueError('Use a unique control password with at least 12 characters.')
    credentials = [bool(settings[name].strip()) for name in
                   ('SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET', 'SPOTIFY_REFRESH_TOKEN')]
    if source != 'preview' and any(credentials) and not all(credentials):
        raise ValueError('Finish connecting Spotify, or clear all three Spotify credential fields.')
    return settings


def server_environment(settings, directory):
    environment = {name: value for name, value in os.environ.items()
                   if not name.startswith(('SPOTIFY_', 'TWITCH_', 'TIKTOK_', 'CHAT_', 'CONTROL_'))}
    for name, value in settings.items():
        if name not in ('PUBLIC_TUNNEL', 'AUTO_OPEN'):
            environment[name] = ('1' if value else '0') if isinstance(value, bool) else value
    environment.update({
        'HOST': '127.0.0.1', 'ALLOWED_ORIGINS': '', 'SECRET_KEY': secrets.token_hex(32),
        'SPOTIFY_MANUAL_QUEUE_STATE_FILE': str(directory / 'spotify_manual_queue_state.json'),
        'PYTHONUNBUFFERED': '1', 'PYTHONIOENCODING': 'utf-8',
        'SPOTIFY_QUEUE_ON_REQUEST': '1' if settings['SPOTIFY_REFRESH_TOKEN'] else '0',
    })
    return environment


def worker_command(directory, session):
    arguments = ['--server', '--data-dir', str(directory), '--session', session, '--parent-pid', str(os.getpid())]
    if getattr(sys, 'frozen', False):
        return [sys.executable, *arguments]
    return [sys.executable, str(resource_path('desktop_launcher.py')), *arguments]


def cloudflared_path():
    bundled = resource_path('cloudflared.exe')
    installed = shutil.which('cloudflared')
    if bundled.is_file():
        return str(bundled)
    if installed:
        return installed
    raise FileNotFoundError('Cloudflare is not bundled or installed. Disable Public HTTPS to use local overlays.')


def port_is_available(port):
    with socket.socket() as probe:
        if os.name == 'nt':
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            probe.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False


class WidgetProcess:
    def __init__(self, directory):
        self.directory = directory
        self.server = None
        self.tunnel = None
        self.session = ''
        self.settings = None
        self.started_at = 0
        self.tunnel_log = None
        self.tunnel_offset = 0
        self.public_origin = ''

    @property
    def origin(self):
        return f"http://127.0.0.1:{self.settings['PORT']}"

    def start(self, settings):
        settings = validate_settings(settings)
        if self.server is not None:
            raise RuntimeError('Stop the running widget before starting another.')
        if not port_is_available(int(settings['PORT'])):
            raise ValueError(f"Port {settings['PORT']} is already in use. Choose another port; no other apps were stopped.")
        if settings['PUBLIC_TUNNEL']:
            cloudflared_path()
        save_settings(self.directory, settings)
        self.settings = settings
        self.session = secrets.token_hex(16)
        self.public_origin = ''
        (self.directory / 'last_tunnel_urls.txt').write_text('No public tunnel is running.\n', encoding='utf-8')
        self.server = subprocess.Popen(
            worker_command(self.directory, self.session), cwd=self.directory,
            env=server_environment(settings, self.directory), stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        self.started_at = time.monotonic()

    def ready(self):
        if self.server is None or self.server.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(self.origin + '/_desktop_health', timeout=0.3) as response:
                return json.load(response).get('session') == self.session
        except (OSError, ValueError):
            return False

    def start_tunnel(self):
        self.tunnel_offset = 0
        self.tunnel_log = (self.directory / 'cloudflared.log').open('wb')
        self.tunnel = subprocess.Popen(
            [cloudflared_path(), 'tunnel', '--no-autoupdate', '--url', self.origin],
            cwd=self.directory, stdin=subprocess.DEVNULL, stdout=self.tunnel_log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )

    def read_tunnel_origin(self):
        if not self.tunnel or self.public_origin:
            return self.public_origin
        with (self.directory / 'cloudflared.log').open('rb') as log:
            log.seek(self.tunnel_offset)
            chunk = log.read()
            complete = chunk.rfind(b'\n') + 1
            self.tunnel_offset += complete
        match = TUNNEL_URL_PATTERN.search(chunk[:complete].decode('utf-8', errors='replace'))
        if match:
            self.public_origin = match.group(0)
            (self.directory / 'last_tunnel_urls.txt').write_text(
                f'Skip Overlay: {self.public_origin}/\nQueue Overlay: {self.public_origin}/queue_widget\n', encoding='utf-8')
        return self.public_origin

    def stop(self):
        try:
            if self.tunnel is not None:
                stop_tunnel(self.tunnel)
        finally:
            if self.tunnel_log is not None:
                self.tunnel_log.close()
            if self.server is not None:
                stop_file = self.directory / (self.session + '.stop')
                stop_file.touch()
                try:
                    self.server.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    stop_tunnel(self.server)
                stop_file.unlink(missing_ok=True)
            self.server = self.tunnel = self.tunnel_log = None
            self.public_origin = ''
            (self.directory / 'last_tunnel_urls.txt').write_text('No public tunnel is running.\n', encoding='utf-8')


def watch_parent(parent_pid, stop_file):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True) if os.name == 'nt' else None
    handle = None
    if kernel and parent_pid:
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        handle = kernel.OpenProcess(0x00100000, False, parent_pid)
        if not handle:
            os._exit(1)
    while not stop_file.exists():
        if handle and kernel.WaitForSingleObject(handle, 0) != 258:
            break
        time.sleep(0.2)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)


def run_server(arguments):
    directory = arguments.data_dir.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    sys.stdout = sys.stderr = (directory / 'server.log').open('w', encoding='utf-8', buffering=1)
    try:
        threading.Thread(target=watch_parent, args=(arguments.parent_pid, directory / (arguments.session + '.stop')),
                         daemon=True).start()
        import live_widget as widget

        widget.app.add_url_rule('/_desktop_health', 'desktop_health', lambda: {'session': arguments.session})
        if os.environ.get('CHAT_SOURCE') == 'preview':
            widget.AUTO_NEXT_ON_THRESHOLD = False
            widget.AUTO_RESET_SKIP_ENABLED = False
            widget.SPOTIFY_QUEUE_ON_REQUEST = False
            widget.socketio.run(widget.app, host='127.0.0.1', port=widget.PORT,
                                allow_unsafe_werkzeug=True, use_reloader=False, log_output=False)
        else:
            asyncio.run(widget.main())
        return 0
    except Exception:
        traceback.print_exc()
        return 1
