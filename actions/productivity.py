"""
actions/productivity.py — Productivity, Pomodoro timer, Focus Mode, and Morning Briefing ported from Layra.
Supports: Pomodoro timers with background notifications, Focus Mode (DND + quit distractions), and morning briefings.
"""
from __future__ import annotations

import os
import platform
import random
import subprocess
import threading
import time
from datetime import datetime

_OS = platform.system()

_POMODORO_RUNNING = False
_POMODORO_COUNT = 0


def _notify_mac(title: str, message: str):
    if _OS == "Darwin":
        safe_t = title.replace('"', '\\"')
        safe_m = message.replace('"', '\\"')
        script = f'display notification "{safe_m}" with title "{safe_t}" sound name "Glass"'
        subprocess.run(["/usr/bin/osascript", "-e", script], capture_output=True)


def start_pomodoro(parameters: dict = None, **kwargs) -> str:
    """Start a Pomodoro session with work and break durations."""
    global _POMODORO_RUNNING, _POMODORO_COUNT
    if _POMODORO_RUNNING:
        return "A Pomodoro session is already active. Say 'stop pomodoro' to cancel it."

    params = parameters or {}
    work_minutes = params.get("work_minutes", 25)
    break_minutes = params.get("break_minutes", 5)

    try:
        work_minutes = int(work_minutes)
        break_minutes = int(break_minutes)
    except Exception:
        work_minutes = 25
        break_minutes = 5

    _POMODORO_RUNNING = True
    _POMODORO_COUNT += 1
    count = _POMODORO_COUNT

    def _runner():
        global _POMODORO_RUNNING
        _notify_mac(f"🍅 Pomodoro #{count} Started", f"Focus time: {work_minutes} minutes!")

        # Work phase
        for _ in range(work_minutes * 60):
            if not _POMODORO_RUNNING:
                return
            time.sleep(1)

        _notify_mac("🍅 Work Interval Complete! 🎉", f"Take a {break_minutes} minute break!")

        # Break phase
        for _ in range(break_minutes * 60):
            if not _POMODORO_RUNNING:
                return
            time.sleep(1)

        _notify_mac("⚡ Break Over!", "Time to start your next focus session!")
        _POMODORO_RUNNING = False

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    return f"🍅 Pomodoro #{count} started: {work_minutes} min focus → {break_minutes} min break. Stay focused, Sir!"


def stop_pomodoro(parameters: dict = None, **kwargs) -> str:
    """Stops the active Pomodoro session."""
    global _POMODORO_RUNNING
    if not _POMODORO_RUNNING:
        return "No Pomodoro session is currently running."
    _POMODORO_RUNNING = False
    return "🛑 Pomodoro session stopped."


def get_pomodoro_status(parameters: dict = None, **kwargs) -> str:
    """Checks the status of the current Pomodoro session."""
    if _POMODORO_RUNNING:
        return f"🍅 Pomodoro #{_POMODORO_COUNT} is active. Keep going!"
    return f"No Pomodoro running. Completed today: {_POMODORO_COUNT}."


def enable_focus_mode(parameters: dict = None, **kwargs) -> str:
    """Enable focus mode: Turn on Do Not Disturb and close distracting apps."""
    if _OS == "Darwin":
        # Enable DND
        subprocess.run(
            "defaults -currentHost write ~/Library/Preferences/ByHost/com.apple.notificationcenterui doNotDisturb -boolean true",
            shell=True, capture_output=True
        )

        distracting = ["Messages", "Slack", "Discord", "Twitter", "Instagram", "Mail", "TikTok"]
        closed = []
        for app in distracting:
            res = subprocess.run(
                ["/usr/bin/osascript", "-e", f'tell application "{app}" to quit'],
                capture_output=True, text=True
            )
            if res.returncode == 0:
                closed.append(app)

        msg = "🎯 Focus Mode ENABLED: Do Not Disturb turned on."
        if closed:
            msg += f" Closed distracting apps: {', '.join(closed)}."
        return msg
    return "Focus Mode is supported on macOS."


def disable_focus_mode(parameters: dict = None, **kwargs) -> str:
    """Disable focus mode and restore notifications."""
    if _OS == "Darwin":
        subprocess.run(
            "defaults -currentHost write ~/Library/Preferences/ByHost/com.apple.notificationcenterui doNotDisturb -boolean false",
            shell=True, capture_output=True
        )
        return "🔔 Focus Mode DISABLED: Do Not Disturb turned off and notifications restored."
    return "Focus Mode is supported on macOS."


def get_morning_briefing(parameters: dict = None, **kwargs) -> str:
    """Synthesize a complete morning briefing with greeting, time, battery, and tips."""
    now = datetime.now()
    hour = now.hour

    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    parts = [
        f"🌅 {greeting}, Sir!",
        f"📅 Today is {now.strftime('%A, %B %d, %Y')} — {now.strftime('%I:%M %p')}",
    ]

    # Battery
    if _OS == "Darwin":
        try:
            batt = subprocess.run(
                "pmset -g batt | grep -o '[0-9]*%' | head -1",
                shell=True, capture_output=True, text=True
            ).stdout.strip()
            if batt:
                parts.append(f"🔋 Battery: {batt}")
        except Exception:
            pass

    # Calendar events today
    try:
        from actions.calendar_manager import get_todays_events
        cal = get_todays_events()
        if cal and "No events" not in cal:
            parts.append(f"\n{cal}")
    except Exception:
        pass

    tips = [
        "💡 Focus Tip: Start with your highest priority task first.",
        "💡 Focus Tip: A 25-minute Pomodoro session will build strong momentum.",
        "💡 Wellness Tip: Stay hydrated, take regular stretch breaks, and rest your eyes.",
        "💡 Productivity Tip: Avoid multitasking; single-tasking yields higher quality code.",
    ]
    parts.append(f"\n{random.choice(tips)}")
    return "\n".join(parts)


def spotlight_search(parameters: dict = None, **kwargs) -> str:
    """Opens macOS Spotlight search with the query pre-filled."""
    query = (parameters or {}).get("query", "").strip()
    if _OS == "Darwin":
        safe_q = query.replace('"', '\\"')
        script = f'''
        tell application "System Events"
            key code 49 using command down
            delay 0.4
            keystroke "{safe_q}"
        end tell
        '''
        subprocess.run(["/usr/bin/osascript", "-e", script], capture_output=True)
        return f"Opened Spotlight search for '{query}'."
    return "Spotlight search is only available on macOS."


# ── Multi-tool declarations (auto-discovered by core/action_loader.py) ───────
TOOLS = [
    {
        "name": "start_pomodoro",
        "description": "Starts a Pomodoro focus timer with customizable work and break intervals and system notifications.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "work_minutes": {
                    "type": "INTEGER",
                    "description": "Work duration in minutes (default: 25)."
                },
                "break_minutes": {
                    "type": "INTEGER",
                    "description": "Break duration in minutes (default: 5)."
                }
            },
            "required": []
        },
        "handler": start_pomodoro,
    },
    {
        "name": "stop_pomodoro",
        "description": "Stops and resets the currently active Pomodoro focus timer.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": stop_pomodoro,
    },
    {
        "name": "get_pomodoro_status",
        "description": "Returns the status of the ongoing Pomodoro timer and count of completed sessions.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": get_pomodoro_status,
    },
    {
        "name": "enable_focus_mode",
        "description": "Enables Focus Mode: turns on Do Not Disturb and closes distracting applications.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": enable_focus_mode,
    },
    {
        "name": "disable_focus_mode",
        "description": "Disables Focus Mode and restores notifications.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": disable_focus_mode,
    },
    {
        "name": "get_morning_briefing",
        "description": "Provides a comprehensive briefing including time, battery status, today's schedule, and productivity tip.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": get_morning_briefing,
    },
    {
        "name": "spotlight_search",
        "description": "Triggers macOS Spotlight search bar with the specified query.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Query string to search in Spotlight."
                }
            },
            "required": ["query"]
        },
        "handler": spotlight_search,
    }
]
