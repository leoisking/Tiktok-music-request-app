Note: If Windows shows a SmartScreen warning, click More info → Run anyway. This is expected for unsigned open-source apps.


# Live Widget

Live Widget is a real-time song-request and skip-voting overlay for TikTok Live and Twitch. It includes transparent OBS/TikTok Studio overlays, a password-protected control panel, optional Spotify queue integration, and a standalone Windows launcher.

## Highlights

- TikTok, Twitch, or combined live-chat input
- `!req` song requests and `!skip` voting
- Adaptive or fixed skip thresholds
- Separate skip and queue browser-source overlays
- Password-protected moderator controls
- Optional Spotify playback and queue integration
- Optional Cloudflare HTTPS links for TikTok Studio
- Standalone Windows EXE with protected per-user settings

## Choose a setup

| Setup | Best for | Requirements |
| --- | --- | --- |
| Windows app | Streamers who want a graphical launcher | 64-bit Windows 10 or 11 |
| Python source | Development and customization | Python 3.14 and project dependencies |
| Batch launcher | Existing Windows source installations | Python, Cloudflare, and environment configuration |

## Windows app quick start

1. Download a published `LiveWidget-Windows-x64.zip` release, or build it from source.
2. Extract the ZIP before opening the app. Do not run the EXE from inside the compressed folder.
3. Open `LiveWidget.exe` and leave the chat source on **Preview** for the first test.
4. Copy the generated control password and select **Start preview**.
5. Paste the password into the control panel that opens in your browser.
6. Open **Overlay links** and copy the skip or queue URL into an OBS browser source.

Settings, credentials, logs, and queue state are stored under `%LOCALAPPDATA%\LiveWidget`. Replacing the EXE does not remove those settings.

See [DISTRIBUTION.md](DISTRIBUTION.md) for the complete recipient and distribution guide.

## Overlay URLs

| Page | Local URL | Safe to show on stream? |
| --- | --- | --- |
| Skip overlay | `http://127.0.0.1:5000/` | Yes |
| Queue overlay | `http://127.0.0.1:5000/queue_widget` | Yes |
| Control panel | `http://127.0.0.1:5000/control` | **No** |

The control panel always requires `CONTROL_PASSWORD`, including from the same computer. Never place the control URL or password in an on-stream source.

## Chat commands

### Viewers

| Command | Action |
| --- | --- |
| `!req Song by Artist` | Add a song request |
| `!skip` | Vote to skip the current song |

### Moderators

| Command | Action |
| --- | --- |
| `!clear` | Clear local song requests |
| `!reset` or `!next` | Reset skip votes |
| `!threshold 8` | Set a temporary threshold |
| `!threshold auto` | Return to automatic/fixed configuration |

Moderator entries are account usernames or stable IDs, not display names. Prefix Twitch entries with `twitch:` when configuring `MOD_LIST`.

## Spotify and public HTTPS

Spotify is optional. Each distributor or user must provide credentials for their own Spotify developer app and authorize their own account. The launcher protects saved secrets with Windows DPAPI for the current Windows user.

For TikTok Studio, select **Public HTTPS** in the launcher. The bundled Cloudflare client creates temporary HTTPS overlay links. Quick Tunnel URLs change when restarted and do not provide an uptime guarantee.

Live chat, Spotify, Cloudflare, fonts, and Socket.IO CDN assets require internet access. Preview mode does not connect to live chat or control playback.

## Run from source

Clone the repository, create a virtual environment, and install the runtime dependencies:

```powershell
git clone https://github.com/leoisking/flask-tiktok-socket-setup.git
cd flask-tiktok-socket-setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Set at least a control password and the account required by your chat source:

```powershell
$env:CHAT_SOURCE = "tiktok"
$env:TIKTOK_USER = "your_username"
$env:CONTROL_PASSWORD = "replace-with-a-long-unique-password"
python live_widget.py
```

For Twitch, use `CHAT_SOURCE=twitch` and set `TWITCH_CHANNEL`. Use `CHAT_SOURCE=both` to connect both services.

Leave `ALLOWED_ORIGINS` unset for same-origin overlays. Wildcard origins are intentionally rejected.

## Build the Windows release

On 64-bit Windows with Python 3.14 installed:

```powershell
.\build_windows.bat
```

The build creates an isolated environment, installs pinned build dependencies, runs the test suite, embeds `LiveWidget.ico`, packages a checksum-verified Cloudflare binary, smoke-tests the standalone EXE, and writes:

```text
dist/LiveWidget.exe
dist/LiveWidget-Windows-x64.zip
```

The `build/`, `dist/`, local credentials, logs, and runtime state are intentionally excluded from Git. Publish the ZIP through GitHub Releases when you want users to download a binary update.

## Test

Run the isolated Python tests:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Optional browser-overlay checks require Node.js and Playwright:

```powershell
npm install --no-save playwright
npx playwright install chromium
node tests/test_overlays.cjs
```

The build process also runs a standalone EXE smoke test covering the GUI, local HTTP pages, WebSocket authentication, protected settings, and clean shutdown.

## Project layout

```text
desktop_launcher.py      Windows desktop entry point
desktop_ui.py            Launcher presentation and interaction layer
desktop_runtime.py       Settings and process management
live_widget.py           Flask/Socket.IO server and chat integrations
index.html               Skip overlay and control workspace
queue_widget.html        Queue overlay
spotify_oauth_helper.py  Local Spotify OAuth flow
tests/                    Backend, launcher, security, and UI tests
LiveWidget.spec           PyInstaller configuration
build_windows.py          Reproducible Windows build pipeline
```

## Security and privacy

Read [SECURITY.md](SECURITY.md) before exposing the widget through a public tunnel. In particular:

- Use a unique control password.
- Keep the control panel off-stream.
- Do not commit `.env`, `spotify_env.bat`, logs, queue state, tokens, or build output.
- Rotate credentials that were previously shared or committed.
- Test real account connections before going live.

## Troubleshooting

- **The EXE icon looks generic:** extract the ZIP first. Windows can show a generic icon inside compressed-folder views; refresh Explorer if an older icon is cached.
- **The port is busy:** stop the other widget instance or choose another local port.
- **The overlay works but chat does not:** check `server.log` and verify that the configured account is currently live.
- **Spotify does not queue songs:** verify app access, scopes, active playback device, and all three Spotify credentials.
- **The HTTPS link is not ready:** wait briefly, then inspect `cloudflared.log` and restart the session if needed.

## License

This repository does not currently include a software license. Until the owner adds one, no open-source redistribution rights are granted by default. Before public distribution or accepting outside contributions, choose and add a license that matches the intended use of the code and bundled artwork.

Third-party components retain their own licenses. Windows builds include `THIRD_PARTY_LICENSES.txt`.
