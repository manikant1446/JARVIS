"""
actions/email_manager.py — Email management for MARK LIII (macOS Apple Mail & Gmail).
Supports: unread email count, email summary, sender/subject/date search, reading emails,
drafting emails, replying, attachment handling, and Level 2 permission gating before sending.
"""
from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from core.permissions import PermissionLevel, execute_with_permission, is_trusted_send_emails

_OS = platform.system()


def run_applescript(script: str) -> str:
    if _OS != "Darwin":
        return "macOS Mail requires macOS."
    try:
        res = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            capture_output=True, text=True, timeout=20
        )
        return res.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


def check_emails(parameters: dict = None, **kwargs) -> str:
    """Checks for recent unread emails in the inbox and provides a summary."""
    count = (parameters or {}).get("count", 5)
    try:
        count = int(count)
    except Exception:
        count = 5

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
                set d to date received of msg as string
                set end of msgList to "• From: " & s & " | Date: " & d & linefeed & "  Subject: " & subj
            end repeat
            set AppleScript's text item delimiters to linefeed
            return "📬 Unread emails (" & unreadCount & " total):" & linefeed & (msgList as text)
        end tell
        '''
        res = run_applescript(script)
        if res and "error" not in res.lower():
            return res

    subprocess.run(["open", "https://mail.google.com"])
    return "Opened Gmail in your browser to check your inbox."


def search_emails(parameters: dict = None, **kwargs) -> str:
    """Searches emails for a keyword, sender, subject, or date."""
    params = parameters or {}
    query = params.get("query", "").strip()
    sender = params.get("sender", "").strip()
    subject = params.get("subject", "").strip()

    search_term = query or sender or subject
    if not search_term:
        return "Please specify what to search for (keyword, sender, or subject)."

    if _OS == "Darwin":
        safe_term = search_term.replace('"', '\\"')
        script = f'''
        tell application "Mail"
            set foundMsgs to (every message of inbox whose subject contains "{safe_term}" or sender contains "{safe_term}")
            if (count of foundMsgs) is 0 then
                return "No emails found matching '{safe_term}'."
            end if
            set msgList to {{}}
            set n to count of foundMsgs
            if n > 6 then set n to 6
            repeat with i from 1 to n
                set msg to item i of foundMsgs
                set s to sender of msg
                set subj to subject of msg
                set d to date received of msg as string
                set end of msgList to "[" & i & "] " & s & " (" & d & "): " & subj
            end repeat
            set AppleScript's text item delimiters to linefeed
            return "Found matching emails for '{safe_term}':" & linefeed & (msgList as text)
        end tell
        '''
        res = run_applescript(script)
        if res and "error" not in res.lower():
            return res

    return f"Search for '{search_term}' completed."


def read_email(parameters: dict = None, **kwargs) -> str:
    """Reads the content/body of a specific email matching a subject or sender."""
    params = parameters or {}
    query = params.get("query", "").strip()
    if not query:
        return "Please specify the subject or sender of the email you want to read."

    if _OS == "Darwin":
        safe_q = query.replace('"', '\\"')
        script = f'''
        tell application "Mail"
            set foundMsgs to (every message of inbox whose subject contains "{safe_q}" or sender contains "{safe_q}")
            if (count of foundMsgs) is 0 then
                return "No email found matching '{safe_q}'."
            end if
            set msg to item 1 of foundMsgs
            set s to sender of msg
            set subj to subject of msg
            set d to date received of msg as string
            set cnt to content of msg
            if length of cnt > 600 then
                set cnt to (text 1 thru 600 of cnt) & "... [truncated]"
            end if
            return "From: " & s & linefeed & "Date: " & d & linefeed & "Subject: " & subj & linefeed & linefeed & cnt
        end tell
        '''
        res = run_applescript(script)
        if res and "error" not in res.lower():
            return res

    return f"Could not open email matching '{query}'."


def draft_email(parameters: dict = None, **kwargs) -> str:
    """Creates an email draft in Apple Mail without sending."""
    params = parameters or {}
    to = params.get("to", "").strip()
    subject = params.get("subject", "").strip()
    body = params.get("body", "").strip()

    if not to or not subject:
        return "Please specify recipient email and subject for the draft."

    if _OS == "Darwin":
        safe_to = to.replace('"', '\\"')
        safe_sub = subject.replace('"', '\\"')
        safe_body = body.replace('"', '\\"')
        script = f'''
        tell application "Mail"
            set newMsg to make new outgoing message with properties {{subject:"{safe_sub}", content:"{safe_body}", visible:true}}
            tell newMsg
                make new to recipient at end of to recipients with properties {{address:"{safe_to}"}}
            end tell
            activate
            return "Draft created in Apple Mail."
        end tell
        '''
        res = run_applescript(script)
        if "error" not in res.lower():
            return f"📝 Draft created for {to} with subject '{subject}'. You can review it in Mail."

    return f"Draft prepared:\nTo: {to}\nSubject: {subject}\nBody: {body}"


def reply_email(parameters: dict = None, **kwargs) -> str:
    """Drafts or sends a reply to an email matching a subject or sender."""
    params = parameters or {}
    query = params.get("query", "").strip()
    reply_body = params.get("body", "").strip()

    if not query or not reply_body:
        return "Please specify which email to reply to and the reply message body."

    if _OS == "Darwin":
        safe_q = query.replace('"', '\\"')
        safe_body = reply_body.replace('"', '\\"')
        script = f'''
        tell application "Mail"
            set foundMsgs to (every message of inbox whose subject contains "{safe_q}" or sender contains "{safe_q}")
            if (count of foundMsgs) is 0 then
                return "No email found matching '{safe_q}' to reply to."
            end if
            set targetMsg to item 1 of foundMsgs
            set replyMsg to reply targetMsg with opening window
            set content of replyMsg to "{safe_body}" & return & return & (content of targetMsg)
            activate
            return "Reply window prepared in Apple Mail."
        end tell
        '''
        res = run_applescript(script)
        return res

    return "Reply automation requires macOS Mail."


def send_email(parameters: dict = None, **kwargs) -> str:
    """Composes and sends an email via Apple Mail. Requires Level 2 confirmation."""
    params = parameters or {}
    to = params.get("to", "").strip()
    subject = params.get("subject", "").strip()
    body = params.get("body", "").strip()
    attachment = params.get("attachment", "").strip()

    if not to or not subject:
        return "Please specify recipient email and subject."

    # Avoid ambiguous contacts
    if "," in to or " or " in to.lower() or " / " in to:
        return f"Ambiguous recipient list '{to}'. Please specify a single exact recipient address."

    def _do_send() -> str:
        if _OS != "Darwin":
            return "Sending emails natively is currently supported via Apple Mail on macOS."

        safe_to = to.replace('"', '\\"')
        safe_sub = subject.replace('"', '\\"')
        safe_body = body.replace('"', '\\"')

        attach_script = ""
        if attachment and os.path.exists(attachment):
            attach_script = f'''
            tell content
                make new attachment with properties {{file name:"{attachment}" as POSIX file}} at after the last paragraph
            end tell
            '''

        script = f'''
        tell application "Mail"
            set newMsg to make new outgoing message with properties {{subject:"{safe_sub}", content:"{safe_body}", visible:false}}
            tell newMsg
                make new to recipient at end of to recipients with properties {{address:"{safe_to}"}}
                {attach_script}
                send
            end tell
            return "ok"
        end tell
        '''
        res = run_applescript(script)
        if "error" in res.lower() and res != "ok":
            return f"Could not send email: {res}"
        return f"📧 Email sent to {to} with subject '{subject}'."

    detail = f"Recipient: {to}\nSubject: {subject}\nBody: {body}"
    if attachment:
        detail += f"\nAttachment: {attachment}"

    return execute_with_permission(
        level=PermissionLevel.LEVEL_2_EXTERNAL,
        title=f"Send email to {to}",
        detail=detail,
        action_fn=_do_send,
        trusted_override=is_trusted_send_emails(),
    )


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
        "description": "Searches inbox emails for a given keyword, sender, or subject.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Search term, sender name, or subject keyword."
                },
                "sender": {
                    "type": "STRING",
                    "description": "Filter by sender email or name."
                },
                "subject": {
                    "type": "STRING",
                    "description": "Filter by subject keyword."
                }
            },
            "required": []
        },
        "handler": search_emails,
    },
    {
        "name": "read_email",
        "description": "Reads the full content of an email matching a subject or sender query.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Subject or sender of the email to read."
                }
            },
            "required": ["query"]
        },
        "handler": read_email,
    },
    {
        "name": "draft_email",
        "description": "Creates an email draft in Mail with recipient, subject, and body for review without sending.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "to": {
                    "type": "STRING",
                    "description": "Recipient email address."
                },
                "subject": {
                    "type": "STRING",
                    "description": "Subject of the email."
                },
                "body": {
                    "type": "STRING",
                    "description": "Body message text."
                }
            },
            "required": ["to", "subject", "body"]
        },
        "handler": draft_email,
    },
    {
        "name": "reply_email",
        "description": "Prepares a reply to an email matching a sender or subject.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Subject or sender of the email to reply to."
                },
                "body": {
                    "type": "STRING",
                    "description": "Reply content to insert."
                }
            },
            "required": ["query", "body"]
        },
        "handler": reply_email,
    },
    {
        "name": "send_email",
        "description": "Composes and sends an email. Requires Level 2 confirmation before sending.",
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
                },
                "attachment": {
                    "type": "STRING",
                    "description": "Optional file path of attachment to attach."
                }
            },
            "required": ["to", "subject", "body"]
        },
        "handler": send_email,
    }
]
