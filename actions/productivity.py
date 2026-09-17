"""
actions/productivity.py — Productivity, Pomodoro, Countdown Timers, Stopwatch, Focus Mode, Quick Notes, and Task Management.
"""
from __future__ import annotations

import json
import os
import platform
import random
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

_OS = platform.system()

_POMODORO_RUNNING = False
_POMODORO_COUNT = 0

# Timers & Stopwatch state
_ACTIVE_TIMERS: dict[str, dict] = {}
_STOPWATCH_START: float | None = None
_STOPWATCH_LAPS: list[float] = []

NOTES_FILE = Path.home() / ".mark_liii_notes.json"
TASKS_FILE = Path.home() / ".mark_liii_tasks.json"


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


def start_countdown_timer(parameters: dict = None, **kwargs) -> str:
    """Starts a countdown timer for a specified number of minutes or seconds."""
    params = parameters or {}
    duration_min = params.get("minutes", 0)
    duration_sec = params.get("seconds", 0)
    label = params.get("label", "").strip() or f"Timer-{int(time.time())}"

    try:
        total_seconds = int(duration_min) * 60 + int(duration_sec)
    except Exception:
        total_seconds = 60

    if total_seconds <= 0:
        return "Please specify a positive duration for the timer."

    timer_id = label.lower()
    _ACTIVE_TIMERS[timer_id] = {
        "label": label,
        "total_seconds": total_seconds,
        "started_at": time.time(),
        "cancelled": False
    }

    def _timer_worker():
        t_data = _ACTIVE_TIMERS.get(timer_id)
        if not t_data:
            return
        time.sleep(total_seconds)
        if not t_data.get("cancelled", False):
            _notify_mac(f"⏰ Timer Finished: {label}", f"Time is up! ({total_seconds // 60} min {total_seconds % 60} sec)")
            if timer_id in _ACTIVE_TIMERS:
                del _ACTIVE_TIMERS[timer_id]

    threading.Thread(target=_timer_worker, daemon=True).start()
    mins, secs = total_seconds // 60, total_seconds % 60
    return f"⏱️ Countdown timer '{label}' set for {mins}m {secs}s."


def stop_countdown_timer(parameters: dict = None, **kwargs) -> str:
    """Stops an active countdown timer."""
    label = (parameters or {}).get("label", "").strip().lower()
    if label and label in _ACTIVE_TIMERS:
        _ACTIVE_TIMERS[label]["cancelled"] = True
        del _ACTIVE_TIMERS[label]
        return f"⏱️ Timer '{label}' cancelled."
    elif _ACTIVE_TIMERS:
        # Cancel newest
        last_k = list(_ACTIVE_TIMERS.keys())[-1]
        _ACTIVE_TIMERS[last_k]["cancelled"] = True
        del _ACTIVE_TIMERS[last_k]
        return f"⏱️ Timer '{last_k}' cancelled."
    return "No active countdown timers running."


def stopwatch_control(parameters: dict = None, **kwargs) -> str:
    """Controls stopwatch: action can be 'start', 'stop', 'lap', or 'status'."""
    global _STOPWATCH_START, _STOPWATCH_LAPS
    action = (parameters or {}).get("action", "status").strip().lower()

    if action == "start":
        _STOPWATCH_START = time.time()
        _STOPWATCH_LAPS = []
        return "⏱️ Stopwatch started."
    elif action == "lap":
        if not _STOPWATCH_START:
            return "Stopwatch is not running. Say 'start stopwatch' first."
        elapsed = time.time() - _STOPWATCH_START
        _STOPWATCH_LAPS.append(elapsed)
        return f"⏱️ Lap {_STOPWATCH_LAPS.index(elapsed) + 1}: {elapsed:.2f}s."
    elif action == "stop":
        if not _STOPWATCH_START:
            return "Stopwatch is not running."
        elapsed = time.time() - _STOPWATCH_START
        _STOPWATCH_START = None
        laps_str = f" with {len(_STOPWATCH_LAPS)} lap(s)" if _STOPWATCH_LAPS else ""
        return f"⏱️ Stopwatch stopped at {elapsed:.2f}s{laps_str}."
    else:
        if _STOPWATCH_START:
            elapsed = time.time() - _STOPWATCH_START
            return f"⏱️ Stopwatch running: {elapsed:.2f}s."
        return "Stopwatch is currently stopped."


def enable_focus_mode(parameters: dict = None, **kwargs) -> str:
    """Enable focus mode: Turn on Do Not Disturb and close distracting apps."""
    if _OS == "Darwin":
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


def quick_notes(parameters: dict = None, **kwargs) -> str:
    """Manage quick notes: action can be 'add', 'list', or 'clear'."""
    params = parameters or {}
    action = params.get("action", "list").lower()
    text = params.get("note", "").strip()

    notes = []
    if NOTES_FILE.exists():
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                notes = json.load(f)
        except Exception:
            notes = []

    if action == "add":
        if not text:
            return "Please provide text for the note."
        note_entry = {
            "id": len(notes) + 1,
            "text": text,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        notes.append(note_entry)
        try:
            with open(NOTES_FILE, "w", encoding="utf-8") as f:
                json.dump(notes, f, indent=2)
            return f"📝 Note saved: '{text}'"
        except Exception as e:
            return f"Failed to save note: {e}"

    elif action == "clear":
        try:
            if NOTES_FILE.exists():
                NOTES_FILE.unlink()
            return "📝 Quick notes cleared."
        except Exception as e:
            return f"Failed to clear notes: {e}"

    else:
        if not notes:
            return "No quick notes saved."
        out = ["📝 Quick Notes:"]
        for n in notes:
            out.append(f"[{n['id']}] ({n['time']}) {n['text']}")
        return "\n".join(out)


def task_management(parameters: dict = None, **kwargs) -> str:
    """Manage tasks: action can be 'add', 'list', or 'complete'."""
    params = parameters or {}
    action = params.get("action", "list").lower()
    task_desc = params.get("task", "").strip()

    tasks = []
    if TASKS_FILE.exists():
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                tasks = json.load(f)
        except Exception:
            tasks = []

    if action == "add":
        if not task_desc:
            return "Please provide task description."
        task_entry = {
            "id": len(tasks) + 1,
            "title": task_desc,
            "completed": False,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        tasks.append(task_entry)
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)
        return f"✅ Task added: '{task_desc}'"

    elif action == "complete":
        matched = False
        for t in tasks:
            if not t.get("completed") and (task_desc.lower() in t.get("title", "").lower() or task_desc == str(t.get("id"))):
                t["completed"] = True
                matched = True
                break
        if matched:
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=2)
            return f"✅ Task marked as completed: '{task_desc}'"
        return f"No open task matching '{task_desc}' found."

    else:
        open_tasks = [t for t in tasks if not t.get("completed")]
        if not open_tasks:
            return "No open tasks in your task list."
        out = [f"📋 Open Tasks ({len(open_tasks)}):"]
        for t in open_tasks:
            out.append(f"• [{t['id']}] {t['title']}")
        return "\n".join(out)


def get_daily_planning(parameters: dict = None, **kwargs) -> str:
    """Synthesizes calendar events and open tasks into a structured daily plan."""
    now = datetime.now()
    plan = [
        f"🎯 Daily Plan for {now.strftime('%A, %B %d')}:",
        "───────────────────────────────────"
    ]

    # 1. Calendar
    try:
        from actions.calendar_manager import get_todays_events
        events = get_todays_events()
        plan.append("📅 Schedule:")
        plan.append(events)
    except Exception:
        pass

    plan.append("\n📋 Priority Tasks:")
    tasks_res = task_management({"action": "list"})
    plan.append(tasks_res)

    plan.append("\n💡 Recommendation: Complete high-leverage coding tasks first before meetings.")
    return "\n".join(plan)


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
        "name": "start_countdown_timer",
        "description": "Starts a countdown timer with customizable minutes, seconds, and label.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "minutes": {
                    "type": "INTEGER",
                    "description": "Timer duration in minutes."
                },
                "seconds": {
                    "type": "INTEGER",
                    "description": "Timer duration in seconds."
                },
                "label": {
                    "type": "STRING",
                    "description": "Optional label for the timer."
                }
            },
            "required": []
        },
        "handler": start_countdown_timer,
    },
    {
        "name": "stop_countdown_timer",
        "description": "Cancels an active countdown timer by label or the most recent one.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "label": {
                    "type": "STRING",
                    "description": "Label of the timer to cancel."
                }
            },
            "required": []
        },
        "handler": stop_countdown_timer,
    },
    {
        "name": "stopwatch_control",
        "description": "Controls stopwatch: 'start', 'stop', 'lap', or 'status'.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: 'start', 'stop', 'lap', or 'status'."
                }
            },
            "required": ["action"]
        },
        "handler": stopwatch_control,
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
        "name": "quick_notes",
        "description": "Manages quick notes: 'add', 'list', or 'clear'.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "'add', 'list', or 'clear'."
                },
                "note": {
                    "type": "STRING",
                    "description": "Content of the note (required for 'add')."
                }
            },
            "required": ["action"]
        },
        "handler": quick_notes,
    },
    {
        "name": "task_management",
        "description": "Manages productivity tasks: 'add', 'list', or 'complete'.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "'add', 'list', or 'complete'."
                },
                "task": {
                    "type": "STRING",
                    "description": "Task description or ID to complete."
                }
            },
            "required": ["action"]
        },
        "handler": task_management,
    },
    {
        "name": "get_daily_planning",
        "description": "Generates a structured daily plan combining today's schedule, open tasks, and focus tips.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": get_daily_planning,
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
