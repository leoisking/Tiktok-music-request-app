# Security

Live Widget accepts live-chat input, exposes local browser pages, stores account credentials, and can optionally publish overlays through a Cloudflare tunnel. Review these rules before streaming or distributing a build.

## Safe defaults

- Keep `HOST=127.0.0.1` and point Cloudflare at the local server.
- Leave `ALLOWED_ORIGINS` unset for same-origin overlays. `*` is rejected.
- Configure a long, unique `CONTROL_PASSWORD`; an empty password disables browser controls.
- Put only `/` and `/queue_widget` on stream. Keep `/control` private.
- Treat Quick Tunnel URLs as public and temporary.
- Use account usernames or stable IDs for moderators, never display names.

The desktop launcher generates a control password on first use and protects saved passwords and OAuth tokens with Windows DPAPI for the current Windows account. Secrets are decrypted in memory while the app runs; DPAPI does not protect against malware already running as that user.

## Files that must remain private

Do not commit or distribute:

- `.env` files
- `spotify_env.bat`
- `settings.json` from `%LOCALAPPDATA%\LiveWidget`
- `spotify_manual_queue_state.json`
- `last_tunnel_urls.txt`
- `launcher.log`, `server.log`, `cloudflared.log`, or the `logs/` directory
- locally built `build/` and `dist/` directories

Logs may contain account names, viewer names, messages, connection details, and error context. Do not ask users to post complete logs publicly without reviewing and redacting them first.

## Browser controls

Every destructive browser action requires the control password, including actions from localhost. The server does not trust `X-Forwarded-For`, browser-provided moderator fields, or another user's display name.

The control route uses no-store responses and anti-framing headers. Overlay responses use a Content Security Policy and bounded Socket.IO payloads. These controls reduce common risks but do not turn the built-in development server into a general-purpose public web host.

## Spotify and Twitch credentials

Each user should provide credentials for their own Spotify developer app. Do not bundle or share the distributor's client secret, refresh token, Twitch OAuth token, or control password.

Register the Spotify redirect URI exactly as shown by the launcher. Use only the scopes required by the app. Revoke and rotate credentials immediately if they are exposed.

## Reporting a problem

Do not include passwords, tokens, private tunnel URLs, or unredacted logs in a public GitHub issue. If no private security contact is published for the repository, report only a minimal, non-sensitive description and ask the owner for a private contact method.

## Pre-stream checklist

1. Start in Preview and verify both overlays.
2. Confirm the control panel rejects an incorrect password.
3. Test the intended live-chat account and moderator IDs.
4. Test Spotify playback with the intended account and active device.
5. Verify public overlay links contain no control password.
6. Keep the control panel and logs off-stream.
7. Stop the app after the stream so the temporary tunnel closes.
