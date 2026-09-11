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
- Redesigned the launcher to match the overlays: violet accent and navy surfaces, Segoe UI Variable type, a new Home page with a live session card, overlay links, and a set-up checklist, one session indicator in the sidebar, a footer that shows Start or Stop depending on state, toggle switches instead of checkboxes, and OBS size hints beside each overlay link. The app icon is now violet.

### Overlay and backend

- Added TikTok and Twitch chat-source selection, including combined mode.
- Added stable per-platform viewer identities for votes and request cooldowns.
- Added adaptive skip thresholds using chat activity and recent viewer counts.
- Added Spotify queue tracking, playback state, and manual queue-state persistence.
- Added transparent skip-overlay behavior and separate queue-source selection.
- Improved reconnect status, offline behavior, playback timing, and album-art fallback.
- Improved moderator controls, acknowledgements, validation, and rate limits.
- Made `!req` show on the overlay immediately; Spotify search and queue-add now run on a background worker and enrich the entry when they finish.
- Mirrored newly queued tracks into the Spotify "Up Next" list at once and wake the poller instead of waiting for the next interval.
- Moved chat processing off the TikTok and Twitch event loops so a slow request never delays skip votes.
- Reused HTTPS connections to Spotify, stopped searching after a confident match, and ran remaining searches in parallel.
- Cached the Spotify device id and album-art lookups, and moved all Spotify HTTP calls and state-file writes out from under the shared state lock.
- Overlays now try the WebSocket transport before long-polling.
- Redesigned both overlays and the control panel as one "album-art glass" system: frosted cards tinted by the current album art, Plus Jakarta Sans + Inter, calmer motion, album-art thumbnails in every queue row, and a dashboard layout for the control page.
- Added `tests/edge_overlay_check.py`, a headless Microsoft Edge port of the browser overlay checks for machines without Node.
- Spotify HTTPS calls (sign-in, search, queue, polling) now verify certificates with Python 3.13+'s strict RFC 5280 extension checks turned off, so chains from otherwise-trusted TLS-inspection firewalls that omit the Authority Key Identifier are accepted the way browsers accept them. Certificate verification and hostname checks stay on. Certificate failures during sign-in now explain that the network is intercepting HTTPS.
- Switched the Windows media bridge from the unmaintained `winsdk` package to pinned `winrt-*` packages (including `winrt-Windows.Foundation`, which async calls require) in the requirements, the PyInstaller spec, and the launcher self-test.
- Fixed the batch launchers' control-password prompt: values are validated by Python from the environment, so shell metacharacters, whitespace-only input, and a pre-set password are handled correctly and the prompt can no longer loop forever.

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
