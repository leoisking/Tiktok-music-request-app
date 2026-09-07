# Live Widget for Windows

## Quick start

1. Extract the ZIP to a folder on your computer. Double-click `LiveWidget.exe`.
2. Start with chat source `preview` to check the overlays without connecting accounts.
3. On Stream setup, click `Copy control password`, then `Start preview` (or `Start widget` in a live chat mode). The control panel opens in your browser.
4. Paste the password into the control panel to unlock controls. Keep this page off-stream.
5. The launcher switches to Overlay links when ready. Copy the Skip overlay or Queue overlay URL into an OBS browser source.
6. For a real stream, click Stop, choose `tiktok`, `twitch`, or `both`, and enter your own usernames.
7. For TikTok Studio, choose `Public HTTPS` under Overlay destination before starting. Wait for HTTPS overlay links, then copy them into Studio.
8. Keep Live Widget running during your stream. Click Stop or close the window when finished.

No separate Python, pip, or Cloudflare installation is needed. This release targets 64-bit Windows 10/11. Live chat, Spotify, public HTTPS, and the overlay's existing CDN scripts/fonts need internet access. Preview makes no live-chat or playback connections, but the browser still fetches those CDN assets.

The supplied overlay artwork/branding is unchanged. The desktop launcher does not add a theme editor.

## Using the desktop interface

The launcher uses a dark theme, dedicated navigation, and a matching waveform icon. Stream setup has a two-column layout on larger windows and stacks on smaller ones. Pages scroll while Start, Stop, and Save settings stay accessible in the bottom bar.

- **Stream setup:** choose your chat source, enter the relevant usernames, select local or public overlays, and copy your private control password.
- **Overlay links:** copy or open your skip, queue, and private control pages. Links become available only after the local server is ready; HTTPS labels indicate an assigned public link, not a guaranteed live connection.
- **Connections:** connect Spotify in your browser, cancel an unfinished sign-in, or expand Advanced Spotify settings for an existing refresh token/device ID. Optional Twitch bot credentials are here too.
- **Preferences:** set adaptive/fixed voting, moderator IDs, the local port, and automatic browser opening.

Use Tab to move between controls, Ctrl+S to save, and Ctrl+Enter to start when stopped. Copy actions show confirmation without revealing secrets. Show/Hide buttons reveal individual credential fields temporarily; navigating to another page hides them again. Validation errors appear inline and focus the relevant setting. The launcher tracks unsaved changes, asks before discarding them, and confirms before closing a running session. Settings are locked while running or signing in; navigation and copying remain available.

## Spotify (optional)

Open Connections, enter credentials for **your own** Spotify developer app, and click `Connect Spotify`. Register `http://127.0.0.1:8888/callback` exactly as that app's redirect URI. The refresh token is filled in after you authorize. You can also paste an existing token with the necessary playback scopes under Advanced Spotify settings.

Start Spotify and choose an active playback device. Spotify playback API features require an eligible account and appropriate app access; development-mode apps have Spotify-imposed access limits. Packaging does not bypass those restrictions. This build does not share the author's developer credentials or provide a single shared Spotify app for all recipients.

- [Spotify app access and quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes)
- [Spotify redirect URI requirements](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri)

## Settings and privacy

Settings, logs, tunnel URLs, and queue state are stored under `%LOCALAPPDATA%\LiveWidget`, not next to the EXE. Use `Logs & settings folder` to find them. Settings take effect on the next Start. A unique control password is generated on first launch; click `Copy control password` whenever you need it. Existing settings from the previous launcher are preserved.

Passwords, OAuth tokens, and the Spotify client secret are protected with Windows DPAPI for the current Windows account. They are decrypted in memory while running. This does not protect against malware running as that account. Do not distribute your settings or logs; logs can contain chat/account details. Credentials cannot normally be copied to another computer/account; reconnect there instead.

The EXE does not import spotify_env.bat, .env, saved queue state, old tunnel URLs, or other personal files from the source folder. Existing batch launchers remain separate from the desktop app's settings.

Public HTTPS is off by default. Enabling it makes the widget internet-accessible, including its password-protected control route. Keep the password private. Public links change when a new quick tunnel starts; update your broadcast sources. Only read-only overlay links should be shown on stream. The Control panel button always uses the local address.

## Troubleshooting

- Port in use: stop your other widget instance or choose another port. The desktop launcher does not kill unrelated programs.
- Chat not arriving: verify the username and that the account is live. Read server.log for connection details; a running web server does not mean live chat is connected.
- HTTPS not ready: wait briefly, then check cloudflared.log. A link can be assigned before Cloudflare finishes connecting. Stop and Start to retry. Local OBS links work without Cloudflare.
- Startup failure: check launcher.log and server.log in the settings folder.
- Reset: close the app, rename settings.json, then reopen and configure it again.
- This build is unsigned. Windows may warn about an unrecognized publisher. Only run a copy from a trusted source; do not disable antivirus protections.

## For the distributor

Share **LiveWidget-Windows-x64.zip**, which contains the standalone EXE, this guide, third-party notices, and build information. Do not share the project directory, settings folder, or `spotify_env.bat`. Keep the third-party notices with the distribution. Review rights to the existing overlay branding/artwork before distributing it under your own name.

For wider public distribution, sign releases with your own trusted code-signing certificate and test on a clean Windows machine. A signing certificate is not included. Live account authorization, real playback, and live public tunnel behavior still need a pre-stream check with the recipient's accounts.

To rebuild from source, install 64-bit Python 3.14 and run `build_windows.bat`. It creates an isolated `.build-venv`, installs pinned packages, downloads a checksum-verified Cloudflare binary, runs Python regressions, packages only allowlisted assets, smoke-tests the EXE, and produces the ZIP. Network access is required on the build machine. New releases should refresh and retest dependency pins deliberately.

The generated `build/` and `dist/` folders are intentionally excluded from Git. Publish the finished ZIP through a GitHub Release instead of committing generated binaries to the repository.
