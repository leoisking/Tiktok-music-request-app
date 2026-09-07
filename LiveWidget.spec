from pathlib import Path
from PyInstaller.utils.hooks import collect_all, copy_metadata

root = Path(SPECPATH)
datas = [(str(root / name), '.') for name in ('index.html', 'queue_widget.html')]
datas += [(str(root / 'build' / 'THIRD_PARTY_LICENSES.txt'), '.')]
binaries = [(str(root / 'build' / 'vendor' / 'cloudflared.exe'), '.')]
hiddenimports = ['engineio.async_drivers.threading', 'engineio.async_drivers._websocket_wsgi']
for package in ('TikTokLive', 'winsdk'):
    package_data, package_binaries, package_imports = collect_all(package)
    datas += package_data
    binaries += package_binaries
    hiddenimports += package_imports
datas += copy_metadata('TikTokLive', recursive=True)

analysis = Analysis(
    [str(root / 'desktop_launcher.py')], pathex=[str(root)], binaries=binaries,
    datas=datas, hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=['pytest', 'IPython', 'matplotlib', 'numpy'], noarchive=False,
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive, analysis.scripts, analysis.binaries, analysis.datas, [],
    name='LiveWidget', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
    icon=str(root / 'build' / 'LiveWidget.ico'),
)
