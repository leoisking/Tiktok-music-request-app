# 🎵 Live Widget

Live Widget is a real-time song-request and skip-voting overlay for TikTok Live and Twitch. It features transparent OBS/TikTok Studio overlays, a password-protected control panel, optional Spotify queue integration, and a standalone Windows launcher.

> ⚠️ **Note:** If Windows shows a SmartScreen warning during setup, click *More info* → *Run anyway*. This is expected for unsigned open-source applications.

---

## 🔍 App Preview

### Desktop UI
<img width="1123" height="855" alt="Desktop UI Preview" src="https://github.com/user-attachments/assets/d19a5db3-ee7d-4a4c-bc5e-b3cea1d1038e" />

### Queue Overlay Widget
<img width="926" height="891" alt="Queue Overlay Preview" src="https://github.com/user-attachments/assets/818447eb-30a0-4632-af22-a4df4108ddec" />

---

## 📌 Table of Contents
* [Highlights](#toc-highlights)
* [Choose a Setup](#toc-setup)
* [Quick Start Guides](#toc-guides)
  * [Windows App Quick Start](#toc-win-start)
  * [Run from Source (Python)](#toc-src-start)
* [Overlay URLs](#toc-urls)
* [Chat Commands](#toc-commands)
* [Spotify & Public HTTPS](#toc-spotify)
* [Build & Test](#toc-build)
* [Project Architecture](#toc-project)
* [Security & Troubleshooting](#toc-security)






---

## <div id="toc-highlights"></div>✨ Highlights

* **Multi-Platform Chat Input:** Connects seamlessly with TikTok, Twitch, or combined live-chats.
* **Viewer Commands:** Interactive `!req` song requests and `!skip` voting systems.
* **Smart Thresholds:** Uses adaptive or fixed skip thresholds to match your audience size.
* **OBS Integration:** Dispatches separate, transparent skip and queue browser-source overlays.
* **Moderator Control Panel:** Protected via standard dashboard authentication.
* **Spotify Integration:** Optional automated playback handling and queue management.
* **TikTok Studio Compatibility:** Optional Cloudflare HTTPS tunnel integration.
* **Secure Environment:** Packages a standalone Windows EXE with DPAPI-protected user data.

---

## <div id="toc-setup"></div>🛠️ Choose a Setup

| Setup | Best for | Requirements |
| :--- | :--- | :--- |
| **Windows App** | Streamers who want a graphical desktop launcher | 64-bit Windows 10 or 11 |
| **Python Source** | Development, customization, and multi-platform workflows | Python 3.14 + project dependencies |
| **Batch Launcher** | Quick automation for existing local source installations | Python, Cloudflare, & environment configurations |

---

## <div id="toc-guides"></div>🚀 Quick Start Guides

### <div id="toc-win-start"></div>1. Windows App Quick Start
1. Download a published `LiveWidget-Windows-x64.zip` package from the repository releases.
2. **Extract the ZIP file** before opening the app. *Do not run the EXE directly from inside a compressed folder.*
3. Launch `LiveWidget.exe` and leave the chat source set to **Preview** for your first initialization test.
4. Copy the freshly generated control password and click **Start preview**.
5. Paste the password into the configuration panel that launches in your default browser.
6. Open the **Overlay links** window and copy either the skip or queue URL into an OBS browser source.

> ℹ️ *Note: Configuration records, local logs, and active queues are securely retained in `%LOCALAPPDATA%\LiveWidget`. Replacing the `LiveWidget.exe` file during updates will not remove these settings.* See [DISTRIBUTION.md](DISTRIBUTION.md) for full delivery workflows.

### <div id="toc-src-start"></div>2. Run from Source (Python)
Clone the repository, create an isolated virtual environment, and install the required dependencies:

```powershell
git clone https://github.com/leoisking/flask-tiktok-socket-setup.git
cd flask-tiktok-socket-setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Configure your control credentials and your target stream chat platform hook:

```powershell
$env:CHAT_SOURCE = "tiktok"
$env:TIKTOK_USER = "your_username"
$env:CONTROL_PASSWORD = "replace-with-a-long-unique-password"
python live_widget.py
```
* **Twitch Configuration:** Set `$env:CHAT_SOURCE = "twitch"` and supply a target channel to `$env:TWITCH_CHANNEL`.
* **Dual Integration:** Set `$env:CHAT_SOURCE = "both"` to aggregate chat streams simultaneously.
* **Note:** Leave `ALLOWED_ORIGINS` unset to force safe, same-origin restrictions. Wildcards (`*`) are explicitly blocked.

---

## <div id="toc-urls"></div>🗺️ Overlay URLs

| Page View | Local Address Target | Safe to Show on Stream? |
| :--- | :--- | :--- |
| **Skip Overlay** | `http://127.0.0.1:5000/` | **Yes** |
| **Queue Overlay** | `http://127.0.0.1:5000/queue_widget` | **Yes** |
| **Control Panel** | `http://127.0.0.1:5000/control` | 🚫 **No** |

> 🔒 *The dashboard always demands your explicit `CONTROL_PASSWORD`. Never expose the control URL or its password to your live video feed.*

---

## <div id="toc-commands"></div>💬 Chat Commands

### Viewers

| Command | Action Description |
| :--- | :--- |
| ``!req <Song Name> by <Artist>`` | Append a new track choice to the live request queue |
| ``!skip`` | Lodge a community vote to automatically skip the active song |

### Moderators

| Command | Action Description |
| :--- | :--- |
| ``!clear`` | Wipe out all current local song requests |
| ``!reset`` or ``!next`` | Instantly clear the accumulated skip counts |
| ``!threshold <number>`` | Apply a fixed temporary skip vote limit (e.g., `!threshold 8`) |
| ``!threshold auto`` | Revert processing back to automated/calculated metrics |

> 🏷️ *Moderator records require account handles or permanent stable IDs rather than friendly display aliases. Prefix Twitch entries with `twitch:` inside your custom `MOD_LIST` variables.*

---

## <div id="toc-spotify"></div>🎵 Spotify and Public HTTPS

* **Spotify Setup:** Integration is completely optional. Each streamer must register their own developer portal application client, supply custom secrets, and sign in to their profile. Launcher assets wrap these values via **Windows DPAPI encryption** tied directly to the local Windows profile.
* **TikTok Studio Links:** Toggle the **Public HTTPS** option within your graphical interface. The integrated Cloudflare runtime initiates temporary HTTPS proxy links. *Quick Tunnel endpoints change across restarts and do not provide service uptime guarantees.*
* **Network Dependencies:** Real-time chat tracking, Spotify connectivity, Cloudflare tunneling, web fonts, and Socket.IO CDNs demand active internet connections. Running in *Preview Mode* bypasses external platform calls.

---

## <div id="toc-build"></div>🛠️ Build & Test

### Production Building
Compile a packaged standalone 64-bit Windows binary (Requires Python 3.14+):
```powershell
.\build_windows.bat
```
The automated script isolates dependencies, executes the test matrix, links the embedded `LiveWidget.ico` asset, packages verified Cloudflare bin targets, runs automated GUI smoke tests, and exports the final deployment models:
* `dist/LiveWidget.exe`
* `dist/LiveWidget-Windows-x64.zip`

> 🛑 *Build environments (`build/`), distribution objects (`dist/`), localized credentials, application logs, and current queue state arrays are natively blocked by Git ignores. Publish the output ZIP file to GitHub Releases for consumer consumption.*

### Running System Tests
Run the standard Python unit test suites:
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```
Automated browser testing requires Node.js and Playwright framework targets:
```powershell
npm install --no-save playwright
npx playwright install chromium
node tests/test_overlays.cjs
```
Alternatively, execute headless edge checks if Node runtimes are missing:
```powershell
python tests/edge_overlay_check.py --screenshots .\overlay-screenshots
```

---

## <div id="toc-project"></div>📂 Project Architecture

```text
├── desktop_launcher.py      # Windows application core entry point
├── desktop_ui.py            # GUI layer presentation and framework interactions
├── desktop_runtime.py       # Configuration manager and background thread handling
├── live_widget.py           # Core Flask/Socket.IO microserver and chat processing engine
├── index.html               # Frontend presentation for skip overlays and dashboards
├── queue_widget.html        # Frontend presentation for song queue boards
├── spotify_oauth_helper.py  # Localized OAuth validation token handler for Spotify
├── tests/                   # Backend engine, wrapper, security, and rendering tests
├── LiveWidget.spec          # PyInstaller configuration profile
└── build_windows.py         # Reproducible pipeline rules for Windows binary creation
```

---

## <div id="toc-security"></div>🛡️ Security and privacy

Review [SECURITY.md](SECURITY.md) guidelines completely prior to creating active public tunnels. Ensure you:
1. Generate an explicit, unique `CONTROL_PASSWORD`.
2. Keep the administrative control web pages out of your active video screen captures.
3. Prevent raw `.env`, `spotify_env.bat`, localized queue tables, runtime tokens, or `/dist` assets from getting pushed to repository branches.
4. Promptly cycle passwords or access keys if credentials are accidentally exposed or shared.

---

## ❓ Troubleshooting

* **The application icon is generic:** Ensure you have fully extracted your download ZIP before launching. Windows file paths can fail to parse icons accurately inside compressed system screens.
* **The designated network port is busy:** Shut down competing background server runtimes or pick an alternative local port mapping in the GUI settings.
* **Overlays render properly but chat tracking fails:** Inspect your local `server.log` file and verify your specified account destination is live broadcasting.
