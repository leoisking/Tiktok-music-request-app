"""Build an allowlisted, single-file Windows distribution in an isolated venv."""

import hashlib
import ctypes
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile

from desktop_branding import write_windows_icon


ROOT = Path(__file__).resolve().parent
CLOUDFLARED_VERSION = '2026.8.3'
CLOUDFLARED_SHA256 = '83e726ed18ea78c5ad5213c4c3a3a27051393950d2bc8ed4de69bec12d14eaae'


def notify_windows_shell(path):
    if os.name == 'nt':
        shell = ctypes.WinDLL('shell32', use_last_error=True)
        shell.SHChangeNotify(0x00002000, 0x0005, str(path), None)
        shell.SHChangeNotify(0x08000000, 0, None, None)


def download(url, target):
    request = urllib.request.Request(url, headers={'User-Agent': 'LiveWidget-build'})
    with urllib.request.urlopen(request, timeout=120) as response, target.open('wb') as output:
        shutil.copyfileobj(response, output)


def prepare_vendor():
    vendor = ROOT / 'build' / 'vendor'
    vendor.mkdir(parents=True, exist_ok=True)
    binary = vendor / 'cloudflared.exe'
    if not binary.exists() or hashlib.sha256(binary.read_bytes()).hexdigest() != CLOUDFLARED_SHA256:
        download(f'https://github.com/cloudflare/cloudflared/releases/download/{CLOUDFLARED_VERSION}/cloudflared-windows-amd64.exe', binary)
    if hashlib.sha256(binary.read_bytes()).hexdigest() != CLOUDFLARED_SHA256:
        raise RuntimeError('Cloudflare checksum mismatch. Refusing to package or run this download.')
    license_path = vendor / f'cloudflared-{CLOUDFLARED_VERSION}-LICENSE'
    if not license_path.exists():
        download(f'https://raw.githubusercontent.com/cloudflare/cloudflared/{CLOUDFLARED_VERSION}/LICENSE', license_path)
    return license_path


def collect_notices(cloudflare_license):
    sections = ['THIRD-PARTY NOTICES\nLive Widget Windows distribution\n']
    sections.append(f'cloudflared {CLOUDFLARED_VERSION}\n' + cloudflare_license.read_text(encoding='utf-8'))
    for package in sorted(metadata.distributions(), key=lambda item: item.metadata['Name'].lower()):
        sections.append(f"\n{'=' * 72}\n{package.metadata['Name']} {package.version}\n")
        licenses = [entry for entry in package.files or []
                    if '.dist-info' in str(entry) and any(word in entry.name.lower() for word in ('license', 'copying', 'notice'))]
        for entry in licenses:
            sections.append(package.locate_file(entry).read_text(encoding='utf-8', errors='replace'))
        if not licenses:
            sections.append(package.metadata.get('License-Expression') or package.metadata.get('License') or 'See the upstream package for license information.')
        for project_url in package.metadata.get_all('Project-URL') or []:
            sections.append(project_url)
    for path in [Path(sys.base_prefix) / 'LICENSE.txt', *sorted((Path(sys.base_prefix) / 'tcl').rglob('license*'))]:
        if path.is_file():
            sections.append(f'\nPython / Tcl / Tk: {path.name}\n' + path.read_text(encoding='utf-8', errors='replace'))
    (ROOT / 'build' / 'THIRD_PARTY_LICENSES.txt').write_text('\n\n'.join(sections), encoding='utf-8')


def main():
    if os.name != 'nt' or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise RuntimeError('Build this release on 64-bit Windows with 64-bit Python.')
    if sys.prefix == sys.base_prefix:
        raise RuntimeError('Use build_windows.bat so personal/global packages are not bundled.')
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py'], cwd=ROOT, check=True)
    collect_notices(prepare_vendor())
    write_windows_icon(ROOT / 'build' / 'LiveWidget.ico')
    output = ROOT / 'dist'
    if output.exists():
        shutil.rmtree(output)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', str(ROOT / 'LiveWidget.spec')], cwd=ROOT, check=True)
    bundle = output / 'LiveWidget'
    executable = bundle / 'LiveWidget.exe'
    report = ROOT / 'build' / 'exe-self-test.json'
    subprocess.run([str(executable), '--self-test', str(report)], cwd=ROOT / 'build', check=True, timeout=120)
    if not json.loads(report.read_text(encoding='utf-8')).get('ok'):
        raise RuntimeError(f'Executable smoke test failed. See {report}')
    subprocess.run([sys.executable, str(ROOT / 'tests' / 'smoke_exe.py'), str(bundle)], cwd=ROOT, check=True, timeout=180)
    notify_windows_shell(executable)
    shutil.copy2(ROOT / 'DISTRIBUTION.md', bundle / 'READ_ME_FIRST.txt')
    shutil.copy2(ROOT / 'build' / 'THIRD_PARTY_LICENSES.txt', bundle / 'THIRD_PARTY_LICENSES.txt')
    manifest = {
        'application': 'LiveWidget', 'platform': 'Windows x64', 'python': platform.python_version(),
        'cloudflared': CLOUDFLARED_VERSION, 'cloudflared_sha256': CLOUDFLARED_SHA256,
        'exe_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
        'packages': {package.metadata['Name']: package.version for package in metadata.distributions()},
    }
    (bundle / 'build-info.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    with zipfile.ZipFile(output / 'LiveWidget-Windows-x64.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in bundle.rglob('*'):
            if path.is_file():
                archive.write(path, Path('LiveWidget') / path.relative_to(bundle))
    print(f"Ready to share: {output / 'LiveWidget-Windows-x64.zip'}")


if __name__ == '__main__':
    main()
