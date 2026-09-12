# 🎵 Live Widget

Live Widget lets your viewers request songs and vote to skip while you stream on TikTok Live or Twitch. Spotify supplies the now-playing and playback queue, while separate browser-source overlays show your queue and skip meter on stream. A password-protected control panel and standalone Windows launcher keep the setup simple.

> ⚠️ **Note:** If Windows shows a SmartScreen warning during setup, click *More info* → *Run anyway*. This is expected for unsigned open-source applications.

## 🚀 Start here: the beginner setup

The easiest option is the **Windows App** from the latest [GitHub Release](https://github.com/leoisking/Tiktok-music-request-app/releases). You do not need Python, Node.js, or Cloudflare installed when using the released ZIP.

### What you will set up

| Part | What it does |
| :--- | :--- |
| **Spotify connection** | Lets the app read what is playing and add viewer requests to the playback queue. |
| **Queue overlay** | Shows the current song, album art, and upcoming requests in OBS or TikTok Studio. |
| **Skip overlay** | Shows the community skip vote and request activity. |
| **Control panel** | Private page for testing requests, clearing the queue, and managing votes. Never show it on stream. |

### Recommended first session

1. Download and extract `LiveWidget-Windows-x64.zip`. Open the extracted folder and launch `LiveWidget.exe`.
2. Open **Connections** and click **Connect Spotify**. Approve access in your browser, then make sure Spotify is playing on the device you want to use.
3. Open **Stream setup** and leave **Chat source** set to **Preview**. Click **Save settings**, then **Start preview**.
4. Open **Overlay links**. Copy the **Queue overlay** URL into an OBS Browser source. Add the **Skip overlay** URL as a second Browser source.
5. Open the private **Control panel** URL in your own browser and enter the generated control password.
6. Use the control panel test area to send `!req Song Name by Artist`. Confirm the request appears in the queue overlay.
7. Send `!skip` and confirm the skip meter changes. Adjust the vote threshold later under **Preferences**.
8. When the preview works, stop it, select **TikTok**, **Twitch**, or **Both**, enter your channel name, and start the real session.

**Important:** Spotify must be open with an active playback device. The queue overlay displays playback and requests; it does not replace Spotify or start music on its own. Keep the control panel URL and password private.

---

## 🔍 App Preview

### Desktop UI
<img width="1123" height="855" alt="Desktop UI Preview" src="https://github.com/user-attachments/assets/d19a5db3-ee7d-4a4c-bc5e-b3cea1d1038e" />

### Queue Overlay Widget
<img width="957" height="895" alt="image" src="https://github.com/user-attachments/assets/fd513c1d-c113-4272-a334-2790778ccbbf" />


### Control Panel
<img width="1896" height="913" alt="image" src="https://github.com/user-attachments/assets/81af5f7d-b394-4ef9-bfea-eec871f8b942" />


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
* **Spotify Integration:** Connect playback, show now-playing details, and manage viewer requests.
* **TikTok Studio Compatibility:** Optional Cloudflare HTTPS tunnel integration.
* **Secure Environment:** Packages a standalone Windows EXE with DPAPI-protected user data.

---

## <div id="toc-setup"></div>🛠️ Choose a Setup

| Setup | Best for | Requirements |
| :--- | :--- | :--- |
| **Windows App** | Streamers who want a graphical desktop launcher | 64-bit Windows 10 or 11 |
| **Python Source** | Development, customization, and multi-platform workflows | Python 3.14 + project dependencies |
| **Batch Launcher** | Quick automation for existing local source installations | Python, Cloudflare, & environment configurations |

### Before you start

- **Windows app:** use a 64-bit Windows 10 or 11 computer. No Python installation is needed for a release ZIP.
- **Run from source:** use 64-bit Python 3.14 or newer and PowerShell. Preview mode is the fastest way to verify the install.
- **Streaming:** keep the launcher running for the whole stream. OBS browser sources use local URLs; TikTok Studio needs Public HTTPS.
- **Spotify:** recommended for the full experience. Preview mode can test the overlays without connecting it, but now-playing, playback queue, and viewer song requests require Spotify.

---

## <div id="toc-guides"></div>🚀 Quick Start Guides

### <div id="toc-win-start"></div>1. Windows App Quick Start
1. Download a published `LiveWidget-Windows-x64.zip` package from the [repository releases](https://github.com/leoisking/Tiktok-music-request-app/releases).
2. **Extract the ZIP file** before opening the app. *Do not run the EXE directly from inside a compressed folder.*
3. Launch `LiveWidget.exe`, open **Connections**, and click **Connect Spotify**. Approve access in your browser and start playback on the desired Spotify device.
4. Leave the chat source set to **Preview** for your first initialization test, then click **Start preview**.
5. Open **Overlay links** and add the **Queue overlay** and **Skip overlay** URLs as separate OBS Browser sources.
6. Open the private control panel, copy the generated password from **Stream setup**, and use the test area to try `!req` and `!skip`.

**First-run check:** open the skip overlay in a browser before adding it to your scene. You should see the compact vote meter and a connected status. Add the queue overlay as a second Browser source if you want now-playing and up-next information.

> ℹ️ *Note: Configuration records, local logs, and active queues are securely retained in `%LOCALAPPDATA%\LiveWidget`. Replacing the `LiveWidget.exe` file during updates will not remove these settings.* See [DISTRIBUTION.md](DISTRIBUTION.md) for full delivery workflows.

### <div id="toc-src-start"></div>2. Run from Source (Python)
Clone this repository, create an isolated virtual environment, and install the required dependencies:

```powershell
git clone https://github.com/leoisking/Tiktok-music-request-app.git
cd Tiktok-music-request-app
python --version
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

Open these pages after the server starts:

1. `http://127.0.0.1:5000/` for the transparent skip overlay.
2. `http://127.0.0.1:5000/queue_widget` for the queue and now-playing overlay.
3. `http://127.0.0.1:5000/control` for the private moderator panel.

In source mode, environment variables belong to the current PowerShell session. Set them again when you open a new terminal.

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

## 🎬 Stream-day checklist

1. Start in Preview and confirm both browser sources load.
2. Confirm the control panel opens locally and unlocks with the generated password.
3. Switch to TikTok, Twitch, or Both and enter the exact channel/username.
4. If using TikTok Studio, enable Public HTTPS and replace old browser-source URLs after each restart.
5. Send a test request and skip vote before going live.
6. Keep the control panel off-stream and stop the widget when the broadcast ends.

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
