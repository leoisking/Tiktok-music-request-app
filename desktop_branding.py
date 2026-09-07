"""Live Widget branding shared by the window and Windows executable."""

from pathlib import Path
import struct
import zlib
import shutil

def icon_png(size):
    rows = bytearray()
    bars = ((0.24, 0.38, 0.32, 0.62), (0.36, 0.24, 0.44, 0.76),
            (0.48, 0.34, 0.56, 0.66), (0.60, 0.18, 0.68, 0.82),
            (0.72, 0.41, 0.80, 0.59))
    for row in range(size):
        rows.append(0)
        for column in range(size):
            horizontal, vertical = (column + 0.5) / size, (row + 0.5) / size
            corner_horizontal = max(0.17 - horizontal, horizontal - 0.83, 0)
            corner_vertical = max(0.17 - vertical, vertical - 0.83, 0)
            if corner_horizontal ** 2 + corner_vertical ** 2 > 0.17 ** 2:
                color = (15, 21, 31, 0)
            elif any(left <= horizontal <= right and top <= vertical <= bottom for left, top, right, bottom in bars):
                color = (128, 235, 197, 255)
            else:
                color = (22, 34, 46, 255)
            rows.extend(color)

    def chunk(kind, payload):
        return struct.pack('!I', len(payload)) + kind + payload + struct.pack('!I', zlib.crc32(kind + payload))

    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', size, size, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(bytes(rows))) + chunk(b'IEND', b''))


def write_windows_icon(path):
    """Copy the checked-in icon without replacing it with generated artwork."""
    shutil.copy2(Path(__file__).parent / 'LiveWidget.ico', path)
