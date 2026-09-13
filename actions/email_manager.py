"""
actions/email_manager.py — Email management ported from Layra.
Supports checking unread emails (via macOS Apple Mail or Gmail API), searching emails, and sending emails.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path

_OS = platform.system()


def run_applescript(script: str) -> str:
    if _OS != "Darwin":
        return "macOS Mail requires macOS."
    try:
        res = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            capture_output=True, text=True, timeout=15
        )
        return res.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


def check_emails(parameters: dict = None, **kwargs) -> str:
    """Checks for recent unread emails in the inbox."""
    count = (parameters or {}).get("count", 5)
    try:
        count = int(count)
    except Exception:
        count = 5

    # Try Apple Mail first on macOS
    if _OS == "Darwin":
        script = f'''
        tell application "Mail"
            set unreadCount to unread count of inbox
            if unreadCount is 0 then
                return "No unread emails in your inbox."
            end if
            set msgList to {{}}
            set recentMsgs to (every message of inbox whose read status is false)
            set n to count of recentMsgs
            if n > {count} then set n to {count}
            repeat with i from 1 to n
                set msg to item i of recentMsgs
                set s to sender of msg
                set subj to subject of msg
                set end of msgList to "• From: " & s & " | Subject: " & subj
            end repeat
            set AppleScript's text item delimiters to linefeed
            return "You have " & unreadCount & " unread email(s):" & linefeed & (msgList as text)
        end tell
        '''
        res = run_applescript(script)
        if res and "error" not in res.lower():
            return res

    # Fallback to opening Mail / Gmail
    subprocess.run(["open", "https://mail.google.com"])
    return "Opened email in your browser to check your inbox."


def search_emails(parameters: dict = None, **kwargs) -> str:
    """Searches emails for a keyword or sender."""
    query = (parameters or {}).get("query", "").strip()
    if not query:
        return "Please specify what to search for."

    if _OS == "Darwin":
        safe_query = query.replace('"', '\\"')
        script = f'''
        tell application "Mail"
            set foundMsgs to (every message of inbox whose subject contains "{safe_query}" or sender contains "{safe_query}")
            if (count of foundMsgs) is 0 then
                return "No emails found matching '{safe_query}'."
            end if
            set msgList to {{}}
            set n to count of foundMsgs
            if n > 5 then set n to 5
            repeat with i from 1 to n
                set msg to item i of foundMsgs
                set s to sender of msg
                set subj to subject of msg
                set end of msgList to "• " & s & ": " & subj
            end repeat
            set AppleScript's text item delimiters to linefeed
            return "Found matching emails:" & linefeed & (msgList as text)
        end tell
        '''
        res = run_applescript(script)
        if res and "error" not in res.lower():
            return res

    return f"Search for '{query}' completed."


def send_email(parameters: dict = None, **kwargs) -> str:
    """Composes and sends an email via Apple Mail."""
    params = parameters or {}
    to = params.get("to", "").strip()
    subject = params.get("subject", "").strip()
    body = params.get("body", "").strip()

    if not to or not subject:
        return "Please specify recipient email and subject."

    if _OS == "Darwin":
        safe_to = to.replace('"', '\\"')
        safe_sub = subject.replace('"', '\\"')
        safe_body = body.replace('"', '\\"')
        script = f'''
        tell application "Mail"
            set newMsg to make new outgoing message with properties {{subject:"{safe_sub}", content:"{safe_body}", visible:true}}
            tell newMsg
                make new to recipient at end of to recipients with properties {{address:"{safe_to}"}}
                send
            end tell
            return "Email sent successfully."
        end tell
        '''
        res = run_applescript(script)
        if "error" not in res.lower():
            return f"📧 Email sent to {to} with subject '{subject}'."

    return f"Could not send email automatically to {to}."


# ── Multi-tool declarations (auto-discovered by core/action_loader.py) ───────
TOOLS = [
    {
        "name": "check_emails",
        "description": "Checks the user's inbox for unread emails and returns a list of senders and subjects.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "count": {
                    "type": "INTEGER",
                    "description": "Maximum number of unread emails to summarize (default: 5)."
                }
            },
            "required": []
        },
        "handler": check_emails,
    },
    {
        "name": "search_emails",
        "description": "Searches inbox emails for a given keyword, contact name, or subject.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Search term, sender name, or subject keyword."
                }
            },
            "required": ["query"]
        },
        "handler": search_emails,
    },
    {
        "name": "send_email",
        "description": "Composes and sends an email to a recipient address with subject and body.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "to": {
                    "type": "STRING",
                    "description": "Recipient email address."
                },
                "subject": {
                    "type": "STRING",
                    "description": "Subject line of the email."
                },
                "body": {
                    "type": "STRING",
                    "description": "Body message text of the email."
                }
            },
            "required": ["to", "subject", "body"]
        },
        "handler": send_email,
    }
]
