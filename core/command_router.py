"""
core/command_router.py — Central Deterministic Command Router for MARK LIII.

Implements high-speed deterministic pattern matching for common commands
(English, Hindi, Hinglish) to execute instant actions locally without
requiring an LLM round-trip. Complex, conversational, or ambiguous queries
fall through to the Gemini Live LLM.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple


def route_command(text: str, player=None) -> Tuple[bool, str]:
    """
    Attempts to route and execute a command deterministically.
    Returns:
      (handled: bool, result: str)
      If handled is False, the caller should pass text to Gemini Live.
    """
    if not text:
        return False, ""

    raw = text.strip()
    s = raw.lower()

    # ── Emergency Stop (highest priority) ────────────────────────────────────
    if s in ("mark stop", "stop", "emergency stop", "ruk jao", "bas karo", "cancel automation", "jarvis stop"):
        from actions import computer_control
        computer_control.emergency_stop()
        msg = "🛑 Emergency Stop: Active automation and tasks cancelled."
        if player:
            player.write_log(f"SYS: {msg}")
        return True, msg

    # ── Pending Confirmation Resolution (Voice confirmation) ─────────────────
    from core import confirm
    if getattr(confirm, "_pending", None) is not None:
        if s in ("yes", "confirm", "proceed", "haan", "ha", "theek hai", "kardo", "yes please", "sure"):
            confirm.resolve(True)
            return True, "Action confirmed and executed."
        elif s in ("no", "cancel", "don't", "mat karo", "nahin", "nahi", "reject", "stop"):
            confirm.resolve(False)
            return True, "Action cancelled."

    # ── 1. System Control & Hardware ─────────────────────────────────────────
    # Battery
    if any(p in s for p in ["battery kitni hai", "battery status", "check battery", "battery percentage", "charging status", "battery level"]):
        from actions.system_control import get_battery_status
        return True, get_battery_status()

    # Network / WiFi / IP
    if any(p in s for p in ["wifi kya hai", "current wifi", "wifi ssid", "local ip", "my ip", "ip address", "network info", "network status", "wifi check"]):
        from actions.system_control import get_network_info
        return True, get_network_info()

    # Active Window / App
    if any(p in s for p in ["active window", "active app", "kaunsi app active hai", "current window", "focused app", "focused window"]):
        from actions.system_control import get_active_window
        return True, get_active_window()

    # Clipboard
    if any(p in s for p in ["clipboard me kya hai", "read clipboard", "clipboard check", "clipboard text", "clipboard content"]):
        from actions.system_control import get_clipboard_text
        return True, get_clipboard_text()

    # Do Not Disturb / Focus
    if "dnd on" in s or "dnd chalu" in s or "enable dnd" in s or "do not disturb on" in s:
        from actions.system_control import toggle_do_not_disturb
        return True, toggle_do_not_disturb({"enable": True})
    if "dnd off" in s or "dnd band" in s or "disable dnd" in s or "do not disturb off" in s:
        from actions.system_control import toggle_do_not_disturb
        return True, toggle_do_not_disturb({"enable": False})

    # Power & Lock
    if any(p in s for p in ["lock mac", "lock screen", "screen lock", "mac lock karo", "computer lock karo"]):
        from actions.system_control import mac_power_control
        return True, mac_power_control({"action": "lock_screen"})
    if any(p in s for p in ["sleep mac", "mac sleep karo", "mac ko sulao", "put mac to sleep"]):
        from actions.system_control import mac_power_control
        return True, mac_power_control({"action": "sleep_mac"})
    if any(p in s for p in ["empty trash", "trash empty karo", "empty the bin", "clear trash"]):
        from actions.system_control import empty_trash
        return True, empty_trash()

    # Volume & Brightness
    if any(p in s for p in ["volume badhao", "volume up", "increase volume", "aawaz badhao"]):
        from actions.computer_settings import volume_up
        volume_up()
        return True, "Volume increased."
    if any(p in s for p in ["volume kam karo", "volume down", "decrease volume", "aawaz kam karo"]):
        from actions.computer_settings import volume_down
        volume_down()
        return True, "Volume decreased."
    if any(p in s for p in ["mute volume", "mute audio", "mute karo", "volume mute"]):
        from actions.computer_settings import volume_mute
        volume_mute()
        return True, "Audio muted."
    if any(p in s for p in ["brightness badhao", "brightness increase", "brightness up", "screen brightness badhao"]):
        from actions.computer_settings import brightness_up
        brightness_up()
        return True, "Brightness increased."
    if any(p in s for p in ["brightness kam karo", "brightness decrease", "brightness down", "screen brightness kam karo"]):
        from actions.computer_settings import brightness_down
        brightness_down()
        return True, "Brightness decreased."

    # System Performance
    if any(p in s for p in ["cpu usage", "ram usage", "system performance", "system status", "system stats", "computer performance"]):
        from actions.system_monitor import get_system_status
        res = get_system_status()
        return True, f"CPU: {res['cpu_percent']}%, RAM: {res['ram_percent']}%, Uptime: {res['uptime']}"

    # ── 2. Music & Audio ─────────────────────────────────────────────────────
    if any(p in s for p in ["gaana play", "play music", "resume music", "gaana resume"]):
        from actions.music_control import control_music
        return True, control_music({"action": "play"})
    if any(p in s for p in ["gaana pause", "pause music", "gaana roko", "music pause"]):
        from actions.music_control import control_music
        return True, control_music({"action": "pause"})
    if any(p in s for p in ["next track", "next song", "agla gaana", "skip track"]):
        from actions.music_control import control_music
        return True, control_music({"action": "next"})
    if any(p in s for p in ["previous track", "previous song", "pichla gaana"]):
        from actions.music_control import control_music
        return True, control_music({"action": "previous"})

    m_spotify = re.search(r"(?:spotify pe|spotify par|on spotify|play)\s+([a-zA-Z0-9\s]+?)\s+(?:play karo|chalao|play)", s)
    if m_spotify and "chrome" not in s and "youtube" not in s:
        song = m_spotify.group(1).strip()
        from actions.music_control import control_music
        return True, control_music({"action": "play", "song_name": song})

    # ── 3. Calendar ──────────────────────────────────────────────────────────
    if any(p in s for p in ["aaj ka schedule batao", "today's schedule", "todays schedule", "aaj kya schedule hai", "aaj ke events"]):
        from actions.calendar_manager import get_todays_events
        return True, get_todays_events()
    if any(p in s for p in ["is week ke events", "upcoming events", "this week events", "next events"]):
        from actions.calendar_manager import get_upcoming_events
        return True, get_upcoming_events({"days": 7})

    # ── 4. Reminders ─────────────────────────────────────────────────────────
    if any(p in s for p in ["reminders batao", "pending reminders", "list reminders", "reminders check karo"]):
        from actions.calendar_manager import get_reminders
        return True, get_reminders()

    # ── 5. Messaging & Email ─────────────────────────────────────────────────
    if any(p in s for p in ["unread messages", "messages check karo", "kya koi naya message aaya hai", "check messages"]):
        from actions.messaging_tools import get_unread_messages
        return True, get_unread_messages()
    if any(p in s for p in ["unread emails", "unread email", "inbox check karo", "check emails", "emails summarize karo"]):
        from actions.email_manager import check_emails
        return True, check_emails()

    # ── 8. Productivity ──────────────────────────────────────────────────────
    if any(p in s for p in ["morning briefing do", "morning briefing", "daily briefing", "aaj ka briefing"]):
        from actions.productivity import get_morning_briefing
        return True, get_morning_briefing()

    m_pomo = re.search(r"(\d+)\s*(?:minute|min)\s*pomodoro", s)
    if m_pomo:
        mins = int(m_pomo.group(1))
        from actions.productivity import start_pomodoro
        return True, start_pomodoro({"work_minutes": mins})
    if "pomodoro start karo" in s or "start pomodoro" in s:
        from actions.productivity import start_pomodoro
        return True, start_pomodoro({"work_minutes": 25})
    if "stop pomodoro" in s or "pomodoro stop" in s or "pomodoro roko" in s:
        from actions.productivity import stop_pomodoro
        return True, stop_pomodoro()

    # Countdown timer
    m_timer = re.search(r"(\d+)\s*(?:minute|min)\s*(?:ka\s*)?timer", s) or re.search(r"timer\s*(?:of\s*)?(\d+)\s*(?:minute|min)", s)
    if m_timer:
        mins = int(m_timer.group(1))
        from actions.productivity import start_countdown_timer
        return True, start_countdown_timer({"minutes": mins, "label": f"{mins} Min Timer"})

    # ── App Launch & Close ───────────────────────────────────────────────────
    m_open = re.match(r"^(?:open|launch|kholo)\s+([a-zA-Z0-9\s]+)$", s) or re.match(r"^([a-zA-Z0-9\s]+)\s+(?:kholo|launch karo|open karo)$", s)
    if m_open:
        target = m_open.group(1).strip()
        common_apps = {"chrome", "google chrome", "safari", "firefox", "spotify", "vscode", "vs code", "terminal", "finder", "calculator", "notes", "slack", "discord", "whatsapp", "mail"}
        if target in common_apps:
            from actions.open_app import open_app
            return True, open_app({"app_name": target})

    # Not handled deterministically -> hand over to Gemini Live
    return False, ""
