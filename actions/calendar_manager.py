"""
actions/calendar_manager.py — macOS Calendar & Reminders hands-free integration ported from Layra.
Supports: query today's events, upcoming events, add calendar event, check reminders, add reminder, complete reminder.
"""
from __future__ import annotations

import platform
import subprocess
from datetime import datetime, timedelta

_OS = platform.system()


def run_applescript(script: str) -> str:
    if _OS != "Darwin":
        return "macOS Calendar and Reminders require macOS."
    try:
        res = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            capture_output=True, text=True, timeout=15
        )
        return res.stdout.strip()
    except Exception as e:
        return f"AppleScript error: {e}"


def get_todays_events(parameters: dict = None, **kwargs) -> str:
    """Get all events scheduled for today from Apple Calendar."""
    if _OS != "Darwin":
        return "Calendar integration is only available on macOS."

    script = '''
    set today to current date
    set startOfDay to today - (time of today)
    set endOfDay to startOfDay + 86399

    set eventList to {}
    tell application "Calendar"
        set allCalendars to every calendar
        repeat with cal in allCalendars
            set calEvents to (every event of cal whose start date ≥ startOfDay and start date ≤ endOfDay)
            repeat with evt in calEvents
                set evtTime to time string of (start date of evt)
                set evtName to summary of evt
                set end of eventList to evtTime & " - " & evtName
            end repeat
        end repeat
    end tell

    if length of eventList is 0 then
        return "No events scheduled for today."
    end if

    set AppleScript's text item delimiters to linefeed
    return eventList as text
    '''
    res = run_applescript(script)
    return f"📅 Today's Events:\n{res}"


def get_upcoming_events(parameters: dict = None, **kwargs) -> str:
    """Get scheduled events for the next N days (default: 7)."""
    if _OS != "Darwin":
        return "Calendar integration is only available on macOS."

    days = (parameters or {}).get("days", 7)
    try:
        days = int(days)
    except Exception:
        days = 7

    script = f'''
    set today to current date
    set startOfDay to today - (time of today)
    set endDate to startOfDay + ({days} * 86400)

    set eventList to {{}}
    tell application "Calendar"
        set allCalendars to every calendar
        repeat with cal in allCalendars
            set calEvents to (every event of cal whose start date ≥ startOfDay and start date ≤ endDate)
            repeat with evt in calEvents
                set evtDate to date string of (start date of evt)
                set evtTime to time string of (start date of evt)
                set evtName to summary of evt
                set end of eventList to evtDate & " " & evtTime & " - " & evtName
            end repeat
        end repeat
    end tell

    if length of eventList is 0 then
        return "No upcoming events found for the next {days} days."
    end if

    set AppleScript's text item delimiters to linefeed
    return eventList as text
    '''
    res = run_applescript(script)
    return f"📅 Upcoming Events (Next {days} Days):\n{res}"


def add_calendar_event(parameters: dict = None, **kwargs) -> str:
    """Creates a new event in Apple Calendar."""
    if _OS != "Darwin":
        return "Calendar integration is only available on macOS."

    params = parameters or {}
    title = params.get("title", "").strip()
    date_str = params.get("date_str", "").strip()
    duration_minutes = params.get("duration_minutes", 60)

    if not title:
        return "Please specify an event title."

    try:
        duration_minutes = int(duration_minutes)
    except Exception:
        duration_minutes = 60

    if not date_str:
        tomorrow = datetime.now() + timedelta(days=1)
        date_str = tomorrow.strftime("%B %d, %Y at 10:00 AM")

    safe_title = title.replace('"', '\\"')
    script = f'''
    tell application "Calendar"
        set targetCal to first calendar
        make new event at end of events of targetCal with properties {{summary:"{safe_title}", start date:date "{date_str}", end date:(date "{date_str}") + {duration_minutes * 60} seconds}}
    end tell
    return "Event created successfully."
    '''
    res = run_applescript(script)
    if "error" in res.lower():
        return f"Failed to create event: {res}"
    return f"📅 Event created: '{title}' on {date_str} ({duration_minutes} min)."


def get_reminders(parameters: dict = None, **kwargs) -> str:
    """Get all incomplete reminders from Apple Reminders."""
    if _OS != "Darwin":
        return "Apple Reminders is only available on macOS."

    script = '''
    tell application "Reminders"
        set reminderList to {}
        set incompleteReminders to (every reminder whose completed is false)
        repeat with r in incompleteReminders
            set end of reminderList to name of r
        end repeat
        if length of reminderList is 0 then
            return "No pending reminders."
        end if
        set AppleScript's text item delimiters to linefeed
        return reminderList as text
    end tell
    '''
    res = run_applescript(script)
    return f"⏰ Pending Reminders:\n{res}"


def add_reminder(parameters: dict = None, **kwargs) -> str:
    """Adds a new reminder to Apple Reminders."""
    if _OS != "Darwin":
        return "Apple Reminders is only available on macOS."

    params = parameters or {}
    text = params.get("text", "").strip()
    due_date = params.get("due_date", "").strip()

    if not text:
        return "Please provide reminder text."

    safe_text = text.replace('"', '\\"')
    if due_date:
        script = f'''
        tell application "Reminders"
            make new reminder with properties {{name:"{safe_text}", due date:date "{due_date}"}}
        end tell
        return "Reminder created."
        '''
    else:
        script = f'''
        tell application "Reminders"
            make new reminder with properties {{name:"{safe_text}"}}
        end tell
        return "Reminder created."
        '''
    res = run_applescript(script)
    if "error" in res.lower():
        return f"Failed to add reminder: {res}"
    return f"⏰ Reminder added: '{text}'" + (f" due {due_date}" if due_date else "")


def complete_reminder(parameters: dict = None, **kwargs) -> str:
    """Marks a reminder as completed in Apple Reminders."""
    if _OS != "Darwin":
        return "Apple Reminders is only available on macOS."

    name = (parameters or {}).get("name", "").strip()
    if not name:
        return "Please specify the reminder name to mark as complete."

    safe_name = name.replace('"', '\\"')
    script = f'''
    tell application "Reminders"
        set matchingReminders to (every reminder whose name contains "{safe_name}" and completed is false)
        if length of matchingReminders > 0 then
            set completed of first item of matchingReminders to true
            return "Reminder marked as completed."
        else
            return "No matching reminder found."
        end if
    end tell
    '''
    return run_applescript(script)


# ── Multi-tool declarations (auto-discovered by core/action_loader.py) ───────
TOOLS = [
    {
        "name": "get_todays_events",
        "description": "Queries Apple Calendar and returns all events scheduled for today.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": get_todays_events,
    },
    {
        "name": "get_upcoming_events",
        "description": "Queries Apple Calendar for upcoming events over the next N days.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "days": {
                    "type": "INTEGER",
                    "description": "Number of days ahead to search (default: 7)."
                }
            },
            "required": []
        },
        "handler": get_upcoming_events,
    },
    {
        "name": "add_calendar_event",
        "description": "Creates a new event in Apple Calendar with title, date/time string, and duration.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Summary or title of the calendar event."
                },
                "date_str": {
                    "type": "STRING",
                    "description": "Date and time string (e.g. 'October 15, 2026 at 3:00 PM')."
                },
                "duration_minutes": {
                    "type": "INTEGER",
                    "description": "Duration in minutes (default 60)."
                }
            },
            "required": ["title"]
        },
        "handler": add_calendar_event,
    },
    {
        "name": "get_reminders",
        "description": "Fetches all active, incomplete reminders from Apple Reminders.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": get_reminders,
    },
    {
        "name": "add_reminder",
        "description": "Adds a new reminder to Apple Reminders with optional due date.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text": {
                    "type": "STRING",
                    "description": "The reminder task text."
                },
                "due_date": {
                    "type": "STRING",
                    "description": "Optional due date/time string (e.g. 'Tomorrow at 5:00 PM')."
                }
            },
            "required": ["text"]
        },
        "handler": add_reminder,
    },
    {
        "name": "complete_reminder",
        "description": "Marks a specific reminder as completed in Apple Reminders.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {
                    "type": "STRING",
                    "description": "The title or keyword of the reminder to mark as complete."
                }
            },
            "required": ["name"]
        },
        "handler": complete_reminder,
    }
]
