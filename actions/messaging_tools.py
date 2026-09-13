"""
actions/messaging_tools.py — Native Apple Messages (iMessage), WhatsApp, and FaceTime ported from Layra.
Supports: sending iMessages, checking unread messages, sending WhatsApp messages, and starting FaceTime video/audio calls.
"""
from __future__ import annotations

import platform
import subprocess
import time

_OS = platform.system()


def run_applescript(script: str) -> str:
    if _OS != "Darwin":
        return "Apple Messages and FaceTime require macOS."
    try:
        res = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            capture_output=True, text=True, timeout=20
        )
        return res.stdout.strip()
    except Exception as e:
        return f"AppleScript error: {e}"


def send_imessage(parameters: dict = None, **kwargs) -> str:
    """Send an iMessage/SMS to a contact or phone number via macOS Messages."""
    if _OS != "Darwin":
        return "iMessage is only supported on macOS."

    params = parameters or {}
    contact = params.get("contact", "").strip()
    message = params.get("message", "").strip()

    if not contact or not message:
        return "Please provide both recipient contact/number and message text."

    safe_message = message.replace('"', '\\"').replace("'", "\\'")
    safe_contact = contact.replace('"', '\\"')

    script = f'''
    tell application "Messages"
        try
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy "{safe_contact}" of targetService
            send "{safe_message}" to targetBuddy
            return "ok"
        on error
            send "{safe_message}" to buddy "{safe_contact}" of (1st account)
            return "ok"
        end try
    end tell
    '''
    res = run_applescript(script)
    if "error" in res.lower() and res != "ok":
        return f"Could not send iMessage: {res}"
    return f"💬 iMessage sent to {contact}: '{message[:60]}...'" if len(message) > 60 else f"💬 iMessage sent to {contact}: '{message}'"


def get_unread_messages(parameters: dict = None, **kwargs) -> str:
    """Check for unread messages in macOS Messages app."""
    if _OS != "Darwin":
        return "macOS Messages inspection is only supported on macOS."

    script = '''
    tell application "Messages"
        set unreadCount to 0
        set unreadList to {}
        repeat with aChat in chats
            if unread count of aChat > 0 then
                set unreadCount to unreadCount + (unread count of aChat)
                set chatName to name of aChat
                set end of unreadList to chatName & " (" & (unread count of aChat) & " unread)"
            end if
        end repeat
        if unreadCount is 0 then
            return "No unread messages."
        end if
        set AppleScript's text item delimiters to linefeed
        return "Unread messages (" & unreadCount & "):" & linefeed & (unreadList as text)
    end tell
    '''
    return run_applescript(script)


def send_whatsapp_message(parameters: dict = None, **kwargs) -> str:
    """Send a WhatsApp message via WhatsApp desktop app."""
    params = parameters or {}
    contact = params.get("contact", "").strip()
    message = params.get("message", "").strip()

    if not contact or not message:
        return "Please specify both recipient and message text."

    if _OS == "Darwin":
        safe_message = message.replace('"', '\\"').replace("'", "\\'")
        subprocess.run(["open", "-a", "WhatsApp"])
        time.sleep(1.2)

        script = f'''
        tell application "WhatsApp"
            activate
        end tell
        delay 0.8
        tell application "System Events"
            tell process "WhatsApp"
                keystroke "f" using command down
                delay 0.5
                keystroke "{contact}"
                delay 1.0
                key code 36
                delay 0.8
                keystroke "{safe_message}"
                delay 0.4
                key code 36
            end tell
        end tell
        '''
        res = run_applescript(script)
        return f"📱 WhatsApp message sent to {contact}."

    return "WhatsApp desktop automation is optimized for macOS."


def start_facetime(parameters: dict = None, **kwargs) -> str:
    """Start a FaceTime video call with a contact or phone number."""
    contact = (parameters or {}).get("contact", "").strip()
    if not contact:
        return "Please provide contact name, email, or phone number to call."

    if _OS == "Darwin":
        subprocess.run(["open", f"facetime://{contact}"])
        return f"📞 Initiating FaceTime video call with {contact}..."
    return "FaceTime is only available on macOS."


def start_audio_call(parameters: dict = None, **kwargs) -> str:
    """Start a FaceTime audio call with a contact or phone number."""
    contact = (parameters or {}).get("contact", "").strip()
    if not contact:
        return "Please provide contact name, email, or phone number for the call."

    if _OS == "Darwin":
        subprocess.run(["open", f"facetime-audio://{contact}"])
        return f"📞 Initiating audio call with {contact}..."
    return "FaceTime Audio is only available on macOS."


# ── Multi-tool declarations (auto-discovered by core/action_loader.py) ───────
TOOLS = [
    {
        "name": "send_imessage",
        "description": "Sends an iMessage or SMS text message to a contact or phone number using Apple Messages.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "contact": {
                    "type": "STRING",
                    "description": "Recipient contact name, email address, or phone number."
                },
                "message": {
                    "type": "STRING",
                    "description": "Text message content to send."
                }
            },
            "required": ["contact", "message"]
        },
        "handler": send_imessage,
    },
    {
        "name": "get_unread_messages",
        "description": "Checks the Apple Messages app for any unread messages and lists senders.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": get_unread_messages,
    },
    {
        "name": "send_whatsapp_message",
        "description": "Sends a message via WhatsApp desktop application to a recipient.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "contact": {
                    "type": "STRING",
                    "description": "WhatsApp contact or chat name."
                },
                "message": {
                    "type": "STRING",
                    "description": "Message content to send."
                }
            },
            "required": ["contact", "message"]
        },
        "handler": send_whatsapp_message,
    },
    {
        "name": "start_facetime",
        "description": "Starts a FaceTime video call to a contact's phone number or Apple ID email.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "contact": {
                    "type": "STRING",
                    "description": "Contact phone number or email address."
                }
            },
            "required": ["contact"]
        },
        "handler": start_facetime,
    },
    {
        "name": "start_audio_call",
        "description": "Starts a hands-free FaceTime Audio call to a contact or phone number.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "contact": {
                    "type": "STRING",
                    "description": "Contact phone number or email address."
                }
            },
            "required": ["contact"]
        },
        "handler": start_audio_call,
    }
]
