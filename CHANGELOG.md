# Changelog

Notable project changes are documented here. The project does not yet publish numbered application releases, so current work remains under **Unreleased**.

## Unreleased

### Desktop application

- Added a standalone 64-bit Windows launcher and PyInstaller build pipeline.
- Added a dark, responsive desktop interface with guided stream setup.
- Added dedicated pages for overlay links, account connections, and preferences.
- Added Start, Stop, Save, copy, open, sign-in cancellation, and inline validation flows.
- Added a multi-size `LiveWidget.ico` application icon and Explorer refresh notification.
- Added Windows DPAPI protection for locally saved passwords and OAuth credentials.
- Added controlled child-process shutdown and parent-process monitoring.
- Added optional bundled Cloudflare Quick Tunnel support.
- Added browser-based Spotify authorization using each user's own developer app.

### Overlay and backend

- Added TikTok and Twitch chat-source selection, including combined mode.
- Added stable per-platform viewer identities for votes and request cooldowns.
- Added adaptive skip thresholds using chat activity and recent viewer counts.
- Added Spotify queue tracking, playback state, and manual queue-state persistence.
- Added transparent skip-overlay behavior and separate queue-source selection.
- Improved reconnect status, offline behavior, playback timing, and album-art fallback.
- Improved moderator controls, acknowledgements, validation, and rate limits.

### Security

- Required the control password for all browser controls, including loopback clients.
- Removed trust in forwarded addresses, browser-supplied moderator fields, and display names.
- Rejected wildcard Socket.IO origins and defaulted to same-origin behavior.
- Added payload limits, bounded authentication attempts, and stricter field validation.
- Added Content Security Policy, no-store control responses, and anti-framing headers.
- Added TLS certificate verification for Twitch IRC.
- Isolated local credentials, logs, queue state, build output, and tunnel URLs from Git.

### Testing and maintenance

- Added backend, overlay, OAuth, launcher, UI, security, and standalone EXE tests.
- Added checksum verification for the Cloudflare binary used in Windows builds.
- Added third-party license collection and build metadata to release archives.
- Consolidated GitHub documentation around the current launcher and security model.

## Historical 2.0 work

- Introduced responsive overlays, WebSocket updates, song requests, and skip voting.
- Added mobile layouts, accessibility semantics, moderator commands, and basic rate limiting.
- Added initial Cloudflare Tunnel and OBS/TikTok Studio setup support.
