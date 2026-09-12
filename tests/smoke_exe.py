"""Exercise a built EXE from a clean folder, without live services or accounts."""

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request

from websockets.sync.client import connect


def run(executable):
    with tempfile.TemporaryDirectory(prefix='Live Widget standalone test ') as temporary:
        directory = Path(temporary)
        if executable.is_dir():
            standalone_dir = directory / 'LiveWidget'
            shutil.copytree(executable, standalone_dir)
            standalone = standalone_dir / 'LiveWidget.exe'
        else:
            standalone = directory / 'LiveWidget.exe'
            shutil.copy2(executable, standalone)
        report_path = directory / 'self-test.json'
        environment = os.environ.copy()
        for name in tuple(environment):
            if name.startswith(('SPOTIFY_', 'TWITCH_', 'TIKTOK_', 'CHAT_', 'CONTROL_', 'PYTHON')):
                environment.pop(name)
        environment.update({
            'PATH': str(Path(os.environ['SystemRoot']) / 'System32'),
            'CHAT_SOURCE': 'preview', 'CONTROL_PASSWORD': 'standalone-test-password',
            'ALLOWED_ORIGINS': '', 'SPOTIFY_QUEUE_ON_REQUEST': '0', 'HOST': '127.0.0.1',
        })
        subprocess.run([str(standalone), '--self-test', str(report_path)], cwd=directory, env=environment,
                       creationflags=subprocess.CREATE_NO_WINDOW, check=True, timeout=120)
        report = json.loads(report_path.read_text(encoding='utf-8'))
        assert report['ok'], report
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        environment['PORT'] = str(port)
        session = 'standalonecheck'
        process = subprocess.Popen(
            [str(standalone), '--server', '--data-dir', str(directory), '--session', session, '--parent-pid', str(os.getpid())],
            cwd=directory, env=environment, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            origin = f'http://127.0.0.1:{port}'
            deadline = time.monotonic() + 60
            while True:
                try:
                    with urllib.request.urlopen(origin + '/_desktop_health', timeout=0.5) as response:
                        if json.load(response).get('session') == session:
                            break
                except (OSError, ValueError):
                    pass
                if process.poll() is not None or time.monotonic() > deadline:
                    log = directory / 'server.log'
                    raise RuntimeError(log.read_text(encoding='utf-8') if log.exists() else 'Standalone server did not start.')
                time.sleep(0.2)
            for path in ('/', '/queue_widget', '/control'):
                with urllib.request.urlopen(origin + path, timeout=3) as response:
                    assert response.status == 200
                    assert b'<html' in response.read().lower()
            with connect(f'ws://127.0.0.1:{port}/socket.io/?EIO=4&transport=websocket', origin=origin, open_timeout=5) as connection:
                assert connection.recv(timeout=5).startswith('0')
                connection.send('40')
                while not connection.recv(timeout=5).startswith('40'):
                    pass
                connection.send('421["mod_auth",{"password":"standalone-test-password"}]')
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    packet = connection.recv(timeout=5)
                    if packet.startswith('431'):
                        assert json.loads(packet[3:])[0]['success']
                        break
                else:
                    raise RuntimeError('No WebSocket authorization acknowledgement.')
                connection.send('422["mod_auth",{"password":"incorrect-password"}]')
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    packet = connection.recv(timeout=5)
                    if packet.startswith('432'):
                        assert json.loads(packet[3:])[0]['error'] == 'unauthorized'
                        break
                else:
                    raise RuntimeError('No WebSocket rejection acknowledgement.')
            report['standalone_http'] = True
            report['standalone_websocket'] = True
        finally:
            (directory / (session + '.stop')).touch()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
                raise RuntimeError('EXE did not shut down normally.')
        with socket.socket() as probe:
            assert probe.connect_ex(('127.0.0.1', port)) != 0
        report['clean_shutdown'] = True
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    run(parser.parse_args().executable.resolve())
