"""Public Spotify application configuration for the desktop OAuth flow."""

import os


BUNDLED_PUBLIC_CLIENT_ID = "3ca66cdfdcb44325bdbc5b78747cd5a5"
PUBLIC_CLIENT_ID = os.getenv("SPOTIFY_PUBLIC_CLIENT_ID", BUNDLED_PUBLIC_CLIENT_ID).strip()
