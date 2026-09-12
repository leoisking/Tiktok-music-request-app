from pathlib import Path
from PyInstaller.utils.hooks import collect_all, copy_metadata

root = Path(SPECPATH)
datas = [(str(root / name), '.') for name in ('index.html', 'queue_widget.html')]
binaries = []
datas += [(str(root / 'build' / 'vendor' / 'cloudflared.exe'), '.')]
hiddenimports = [
    'engineio.async_drivers.threading', 'engineio.async_drivers._websocket_wsgi',
    # Windows media session bridge (pywinrt). The package is a namespace package, so name the modules explicitly.
    'winrt', 'winrt.system', 'winrt.runtime', 'winrt.runtime._internals', 'winrt._winrt',
    'winrt.windows.foundation', 'winrt._winrt_windows_foundation',
    'winrt.windows.media.control', 'winrt._winrt_windows_media_control',
]
for package in ('TikTokLive', 'winrt'):
    package_data, package_binaries, package_imports = collect_all(package)
    if package != 'TikTokLive':
        datas += package_data
    binaries += package_binaries
    hiddenimports += package_imports
datas += copy_metadata('TikTokLive', recursive=True)
for distribution in ('winrt-runtime', 'winrt-Windows.Foundation', 'winrt-Windows.Media.Control'):
    datas += copy_metadata(distribution)

analysis = Analysis(
    [str(root / 'desktop_launcher.py')], pathex=[str(root)], binaries=binaries,
    datas=datas, hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=['pytest', 'IPython', 'matplotlib', 'numpy'], noarchive=False,
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive, analysis.scripts, [], [], [],
    name='LiveWidget', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
    exclude_binaries=True,
    icon=str(root / 'build' / 'LiveWidget.ico'),
)
bundle = COLLECT(
    executable, analysis.binaries, analysis.datas,
    strip=False, upx=False, name='LiveWidget',
)
