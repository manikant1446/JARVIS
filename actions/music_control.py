"""
actions/music_control.py — Spotify & Apple Music hands-free control ported from Layra.
Supports: play song by name, pause, resume, next, previous, and currently playing info.
Uses Spotify Web Search API for instant track resolution + native macOS AppleScript/URI playback.
"""
from __future__ import annotations

import base64
import json
import os
import platform
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

_OS = platform.system()


def _get_spotify_credentials() -> tuple[str, str]:
    client_id = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        # Check .env or config/api_keys.json
        base_dir = Path(__file__).resolve().parent.parent
        for candidate in [base_dir / ".env", base_dir.parent / "Layra" / ".env", base_dir / "config" / "api_keys.json"]:
            if candidate.exists():
                try:
                    if candidate.suffix == ".json":
                        data = json.loads(candidate.read_text(encoding="utf-8"))
                        client_id = client_id or data.get("spotify_client_id", "")
                        client_secret = client_secret or data.get("spotify_client_secret", "")
                    else:
                        for line in candidate.read_text(encoding="utf-8").splitlines():
                            line = line.strip()
                            if line.startswith("SPOTIFY_CLIENT_ID="):
                                client_id = client_id or line.split("=", 1)[1].strip().strip('"').strip("'")
                            elif line.startswith("SPOTIFY_CLIENT_SECRET="):
                                client_secret = client_secret or line.split("=", 1)[1].strip().strip('"').strip("'")
                except Exception:
                    pass
            if client_id and client_secret:
                break
    return client_id, client_secret


def _get_spotify_track_uri(song_name: str) -> str | None:
    """Search Spotify for a track and return its URI (spotify:track:XXX)."""
    client_id, client_secret = _get_spotify_credentials()
    if not client_id or not client_secret:
        return None

    try:
        auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        token_req = urllib.request.Request(
            "https://accounts.spotify.com/api/token",
            data=b"grant_type=client_credentials",
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with urllib.request.urlopen(token_req, timeout=6) as resp:
            token_data = json.loads(resp.read())
        token = token_data.get("access_token")
        if not token:
            return None

        query = urllib.parse.quote(song_name)
        search_req = urllib.request.Request(
            f"https://api.spotify.com/v1/search?q={query}&type=track&limit=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(search_req, timeout=6) as resp:
            results = json.loads(resp.read())
        tracks = results.get("tracks", {}).get("items", [])
        if tracks:
            return tracks[0]["uri"]
    except Exception as e:
        print(f"[MusicControl] Spotify search failed: {e}")
    return None


def run_applescript(script: str) -> str:
    if _OS != "Darwin":
        return "Only supported on macOS."
    try:
        res = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            capture_output=True, text=True, timeout=10
        )
        return res.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


def control_music(parameters: dict = None, **kwargs) -> str:
    """Controls music playback on Spotify or Apple Music."""
    params = parameters or {}
    action = params.get("action", "play").lower().strip()
    song_name = params.get("song_name", "").strip()

    if _OS != "Darwin":
        # Cross-platform basic media key fallback
        try:
            import pyautogui
            if action in ("pause", "resume", "toggle"):
                pyautogui.press("playpause")
                return "Toggled playback."
            elif action == "next":
                pyautogui.press("nexttrack")
                return "Skipped to next track."
            elif action == "previous":
                pyautogui.press("prevtrack")
                return "Previous track."
        except Exception:
            pass
        return "Full music search and playback requires macOS."

    # 1. Play specific song
    if song_name or action == "play_song":
        target = song_name or action
        track_uri = _get_spotify_track_uri(target)
        if track_uri:
            # Tell Spotify to open and play the URI
            subprocess.run(["open", track_uri])
            time.sleep(0.8)
            run_applescript('tell application "Spotify" to play')
            return f"🎵 Playing '{target}' on Spotify."
        else:
            # Fallback: Search & play directly via Spotify app or Apple Music
            script = f'''
            tell application "Spotify"
                activate
                play track "spotify:search:{target}"
            end tell
            '''
            res = run_applescript(script)
            if "error" not in res.lower():
                return f"🎵 Searching and playing '{target}' on Spotify."
            # Fallback to Apple Music
            script_music = f'''
            tell application "Music"
                activate
                play (first track whose name contains "{target}")
            end tell
            '''
            res_music = run_applescript(script_music)
            if "error" not in res_music.lower():
                return f"🎵 Playing '{target}' on Apple Music."
            return f"Could not find or play '{target}' on Spotify or Apple Music."

    # 2. Pause
    if action == "pause":
        run_applescript('''
        try
            tell application "Spotify" to pause
        end try
        try
            tell application "Music" to pause
        end try
        ''')
        return "Music paused."

    # 3. Resume / Play
    if action in ("play", "resume"):
        script = '''
        if application "Spotify" is running then
            tell application "Spotify" to play
            return "Resumed Spotify."
        else if application "Music" is running then
            tell application "Music" to play
            return "Resumed Apple Music."
        else
            tell application "Spotify" to activate
            tell application "Spotify" to play
            return "Started Spotify playback."
        end if
        '''
        return run_applescript(script)

    # 4. Next Track
    if action == "next":
        run_applescript('''
        if application "Spotify" is running then
            tell application "Spotify" to next track
        else if application "Music" is running then
            tell application "Music" to next track
        end if
        ''')
        return "Skipped to next track."

    # 5. Previous Track
    if action in ("previous", "prev"):
        run_applescript('''
        if application "Spotify" is running then
            tell application "Spotify" to previous track
        else if application "Music" is running then
            tell application "Music" to previous track
        end if
        ''')
        return "Returned to previous track."

    # 6. Current playing track info
    if action in ("current", "now_playing", "info"):
        script = '''
        if application "Spotify" is running then
            tell application "Spotify"
                set trackName to name of current track
                set artistName to artist of current track
                return trackName & " by " & artistName
            end tell
        else if application "Music" is running then
            tell application "Music"
                set trackName to name of current track
                set artistName to artist of current track
                return trackName & " by " & artistName
            end tell
        else
            return "No music player currently running."
        end if
        '''
        res = run_applescript(script)
        return f"Now playing: {res}" if res else "No track playing."

    return f"Unknown music action: {action}"


TOOL = {
    "name": "control_music",
    "description": "Controls music playback on Spotify or Apple Music. Can play specific songs by title, pause, resume, skip tracks, go to previous track, or get current track info.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "One of: play | pause | resume | next | previous | current"
            },
            "song_name": {
                "type": "STRING",
                "description": "The song title and/or artist name to play (e.g. 'Bohemian Rhapsody', 'Shape of You', 'Starboy')."
            }
        },
        "required": ["action"]
    },
    "handler": control_music,
}
