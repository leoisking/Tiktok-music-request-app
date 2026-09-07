"""Start one Cloudflare tunnel and open both overlay pages when reachable."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
import webbrowser


TUNNEL_URL_PATTERN = re.compile(
    r'https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.trycloudflare\.com(?=[/\s|]|$)'
)


def overlay_urls(origin):
    return [('Skip Overlay', origin + '/'), ('Queue Overlay', origin + '/queue_widget')]


def url_is_ready(url):
    request = urllib.request.Request(url, method='HEAD')
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def open_overlays_when_ready(urls, stopped, timeout=90):
    deadline = time.monotonic() + timeout
    while not stopped.is_set() and time.monotonic() < deadline:
        if all(url_is_ready(url) for label, url in urls):
            for label, url in urls:
                if stopped.is_set():
                    return
                try:
                    opened = webbrowser.open_new_tab(url)
                except (OSError, webbrowser.Error):
                    opened = False
                if opened:
                    print(f'[OPENED] {label}: {url}', flush=True)
                else:
                    print(f'[WARNING] Could not open your browser. Open {label} manually: {url}', flush=True)
            return
        if stopped.wait(1):
            return
    if not stopped.is_set():
        print('[WARNING] The public overlays are not reachable yet. The tunnel is still running; '
              'use the saved URLs once Cloudflare finishes connecting.', flush=True)


def stop_tunnel(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def run_tunnel(port, urls_file, auto_open=True):
    stopped = threading.Event()
    browser_worker = None
    process = None
    origin = None
    try:
        urls_file.write_text('Waiting for a new Cloudflare tunnel URL.\n', encoding='utf-8')
        process = subprocess.Popen(
            ['cloudflared', 'tunnel', '--url', f'http://127.0.0.1:{port}'],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding='utf-8', errors='replace', bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        for line in process.stdout:
            print(line, end='', flush=True)
            match = TUNNEL_URL_PATTERN.search(line)
            if origin or not match:
                continue
            origin = match.group(0)
            urls = overlay_urls(origin)
            links = '\n'.join(f'{label}: {url}' for label, url in urls)
            urls_file.write_text(links + '\n', encoding='utf-8')
            print(f'\n{links}\n[INFO] URLs saved to: {urls_file}', flush=True)
            if auto_open:
                print('[INFO] Both overlay pages will open automatically once reachable. '
                      'Keep this launcher running.', flush=True)
                browser_worker = threading.Thread(
                    target=open_overlays_when_ready, args=(urls, stopped), daemon=True,
                )
                browser_worker.start()
            else:
                print('[INFO] Automatic browser opening is disabled by AUTO_OPEN_OVERLAYS.', flush=True)
        return_code = process.wait()
        if not origin:
            print('[ERROR] Cloudflare exited without providing an overlay URL.', flush=True)
            return return_code or 1
        return return_code
    except KeyboardInterrupt:
        print('\n[INFO] Stopping the overlay tunnel...', flush=True)
        return 130
    except OSError as error:
        print(f'[ERROR] Could not run the overlay tunnel: {error}', flush=True)
        return 1
    finally:
        stopped.set()
        if process is not None:
            stop_tunnel(process)
            if process.stdout is not None:
                process.stdout.close()
        if browser_worker is not None:
            browser_worker.join(timeout=7)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--urls-file', type=Path, default=Path(__file__).with_name('last_tunnel_urls.txt'))
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    auto_open = os.getenv('AUTO_OPEN_OVERLAYS', '1').strip().lower() not in ('0', 'false', 'no', 'off')
    return run_tunnel(args.port, args.urls_file, auto_open=auto_open)


if __name__ == '__main__':
    raise SystemExit(main())
