"""Briefly display and capture only the launcher window for Windows visual checks."""

import ctypes
from ctypes import wintypes
from pathlib import Path
import struct
import sys
import tempfile
import time
import tkinter as tk
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from desktop_launcher import DesktopApp


def capture_window(root, output):
    user = ctypes.WinDLL('user32', use_last_error=True)
    graphics = ctypes.WinDLL('gdi32', use_last_error=True)
    user.GetDC.argtypes = [wintypes.HWND]
    user.GetDC.restype = wintypes.HDC
    user.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    graphics.CreateCompatibleDC.argtypes = [wintypes.HDC]
    graphics.CreateCompatibleDC.restype = wintypes.HDC
    graphics.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    graphics.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    graphics.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    graphics.SelectObject.restype = wintypes.HGDIOBJ
    graphics.BitBlt.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
    graphics.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
                                  ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
    graphics.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    graphics.DeleteDC.argtypes = [wintypes.HDC]
    width, height = root.winfo_width(), root.winfo_height()
    handle = root.winfo_id()
    device = user.GetDC(handle)
    memory = graphics.CreateCompatibleDC(device)
    bitmap = graphics.CreateCompatibleBitmap(device, width, height)
    previous = graphics.SelectObject(memory, bitmap)
    try:
        if not graphics.BitBlt(memory, 0, 0, width, height, device, 0, 0, 0x00CC0020):
            raise ctypes.WinError(ctypes.get_last_error())
        graphics.SelectObject(memory, previous)
        header = ctypes.create_string_buffer(struct.pack('<IiiHHIIiiII', 40, width, -height, 1, 32, 0, 0, 0, 0, 0, 0))
        pixels = ctypes.create_string_buffer(width * height * 4)
        if graphics.GetDIBits(memory, bitmap, 0, height, pixels, header, 0) != height:
            raise RuntimeError('Could not read the launcher window bitmap.')
        raw = pixels.raw
        rows = bytearray()
        for row in range(height):
            rows.append(0)
            start = row * width * 4
            for offset in range(start, start + width * 4, 4):
                rows.extend((raw[offset + 2], raw[offset + 1], raw[offset]))

        def chunk(kind, payload):
            return struct.pack('!I', len(payload)) + kind + payload + struct.pack('!I', zlib.crc32(kind + payload))

        output.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', width, height, 8, 2, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(bytes(rows))) + chunk(b'IEND', b''))
    finally:
        graphics.SelectObject(memory, previous)
        graphics.DeleteObject(bitmap)
        graphics.DeleteDC(memory)
        user.ReleaseDC(handle, device)


def main():
    destination = Path(__file__).resolve().parents[1] / 'build' / 'ui-preview'
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='widget-visual-check-') as directory:
        root = tk.Tk()
        root.withdraw()
        app = DesktopApp(root, Path(directory))
        root.geometry('1120x820+60+40')
        root.attributes('-topmost', True)
        root.deiconify()
        root.update()
        try:
            for page in app.view.pages:
                app.view.show_page(page)
                root.update()
                time.sleep(0.15)
                capture_window(root, destination / (page + '.png'))
            app.process.settings = {'PORT': '5000'}
            app.running = True
            app.view.show_page('overlays')
            app.view.set_session('running')
            app.update_urls()
            app.status.set('Preview is running. No live chat or playback connections.')
            root.update()
            capture_window(root, destination / 'running-overlays.png')
            app.running = False
            app.view.set_session('stopped')
            app.view.refresh_settings()
            app.view.show_page('setup')
            root.geometry('900x620+60+40')
            root.update()
            capture_window(root, destination / 'compact-setup.png')
            root.tk.call('tk', 'scaling', 2.0)
            root.geometry('1120x820+60+40')
            root.update()
            capture_window(root, destination / 'large-text-setup.png')
        finally:
            app.destroy()
    print('Launcher-only previews:', destination)


if __name__ == '__main__':
    main()
