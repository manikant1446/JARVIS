"""
actions/system_control.py — Deep native macOS system access ported from Layra.
Hands-free system utilities: battery, network, active window, DND, clipboard,
Finder empty trash, uptime, display sleep, and direct terminal shell execution.
"""
from __future__ import annotations

import os
import platform
import subprocess
import time
from pathlib import Path

_OS = platform.system()


def run_applescript(script: str) -> str:
    if _OS != "Darwin":
        return "AppleScript is only supported on macOS."
    try:
        res = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            capture_output=True, text=True, timeout=15
        )
        return res.stdout.strip()
    except Exception as e:
        return f"AppleScript error: {e}"


def get_battery_status(parameters: dict = None, **kwargs) -> str:
    """Get battery charge, status (charging/discharging) and time remaining."""
    if _OS == "Darwin":
        try:
            res = subprocess.run(
                ["pmset", "-g", "batt"],
                capture_output=True, text=True, timeout=5
            )
            out = res.stdout.strip()
            if not out:
                return "Could not retrieve battery information."
            return f"🔋 Battery Info:\n{out}"
        except Exception as e:
            return f"Battery check failed: {e}"
    elif _OS == "Windows":
        try:
            import psutil
            b = psutil.sensors_battery()
            if b:
                plugged = "Plugged in" if b.power_plugged else "On battery"
                return f"🔋 Battery: {b.percent}% ({plugged})"
        except Exception:
            pass
    return "Battery info not available for this system."


def get_network_info(parameters: dict = None, **kwargs) -> str:
    """Get network details: Wi-Fi SSID, local IP address, and default gateway."""
    info_lines = []
    if _OS == "Darwin":
        # Get active Wi-Fi SSID
        try:
            res = subprocess.run(
                ["networksetup", "-getairportnetwork", "en0"],
                capture_output=True, text=True, timeout=5
            )
            info_lines.append(res.stdout.strip())
        except Exception:
            pass

        # Get IP address
        try:
            res = subprocess.run(
                ["ipconfig", "getifaddr", "en0"],
                capture_output=True, text=True, timeout=5
            )
            ip = res.stdout.strip()
            if ip:
                info_lines.append(f"Local IP (en0): {ip}")
        except Exception:
            pass

    # Public IP / general fallback
    try:
        import urllib.request
        req = urllib.request.Request("https://api.ipify.org", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            info_lines.append(f"Public IP: {resp.read().decode('utf-8').strip()}")
    except Exception:
        pass

    return "\n".join(info_lines) if info_lines else "Could not obtain network details."


def get_active_window(parameters: dict = None, **kwargs) -> str:
    """Returns frontmost active application and window title."""
    if _OS == "Darwin":
        script = '''
        tell application "System Events"
            set frontApp to first application process whose frontmost is true
            set appName to name of frontApp
            try
                set winTitle to name of front window of frontApp
                return appName & " — " & winTitle
            on error
                return appName
            end try
        end tell
        '''
        res = run_applescript(script)
        return f"Active Window: {res}" if res else "No active window detected."
    return "Active window query only supported on macOS."


def toggle_do_not_disturb(parameters: dict = None, **kwargs) -> str:
    """Toggles or sets macOS Do Not Disturb / Focus mode."""
    enable = (parameters or {}).get("enable", True)
    if _OS == "Darwin":
        val = "true" if enable else "false"
        cmd = f"defaults -currentHost write ~/Library/Preferences/ByHost/com.apple.notificationcenterui doNotDisturb -boolean {val}"
        subprocess.run(cmd, shell=True, capture_output=True)
        state_str = "enabled" if enable else "disabled"
        return f"Do Not Disturb (Focus) {state_str}."
    return "Do Not Disturb control only supported on macOS."


def get_clipboard_text(parameters: dict = None, **kwargs) -> str:
    """Reads current text contents from the system clipboard."""
    if _OS == "Darwin":
        try:
            res = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=3)
            clip = res.stdout
            if not clip:
                return "Clipboard is currently empty."
            return f"Clipboard contents:\n{clip[:1000]}"
        except Exception as e:
            return f"Failed to read clipboard: {e}"
    try:
        import pyperclip
        text = pyperclip.paste()
        return f"Clipboard contents:\n{text[:1000]}" if text else "Clipboard is empty."
    except Exception as e:
        return f"Could not read clipboard: {e}"


def copy_to_clipboard(parameters: dict = None, **kwargs) -> str:
    """Copies given text to the system clipboard."""
    text = (parameters or {}).get("text", "")
    if not text:
        return "No text provided to copy."
    if _OS == "Darwin":
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"), timeout=3)
            return f"Copied to clipboard: '{text[:60]}...'" if len(text) > 60 else f"Copied to clipboard: '{text}'"
        except Exception as e:
            return f"Failed to copy to clipboard: {e}"
    try:
        import pyperclip
        pyperclip.copy(text)
        return "Text copied to clipboard."
    except Exception as e:
        return f"Could not copy text: {e}"


def empty_trash(parameters: dict = None, **kwargs) -> str:
    """Empties macOS Finder trash."""
    if _OS == "Darwin":
        script = 'tell application "Finder" to empty trash'
        run_applescript(script)
        return "Trash emptied successfully."
    return "Trash emptying is supported on macOS."


def run_shell_command(parameters: dict = None, **kwargs) -> str:
    """Executes a shell command hands-free and returns output."""
    command = (parameters or {}).get("command", "").strip()
    if not command:
        return "No command specified."
    try:
        res = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        out = res.stdout.strip()
        err = res.stderr.strip()
        if out and err:
            return f"{out}\n[stderr]:\n{err}"
        elif out:
            return out[:2500]
        elif err:
            return f"[stderr]:\n{err}"
        return f"Command executed with code {res.returncode}."
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds."
    except Exception as e:
        return f"Command execution failed: {e}"


def mac_power_control(parameters: dict = None, **kwargs) -> str:
    """Handles lock_screen, sleep_mac, sleep_display, or uptime."""
    action = (parameters or {}).get("action", "").lower().strip()
    if action == "lock_screen":
        if _OS == "Darwin":
            subprocess.run(
                ["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-suspend"]
            )
            return "Screen locked."
        return "Screen lock initiated."
    elif action == "sleep_display":
        if _OS == "Darwin":
            subprocess.run(["pmset", "displaysleepnow"])
            return "Display put to sleep."
        return "Display sleeping."
    elif action == "sleep_mac":
        if _OS == "Darwin":
            run_applescript('tell application "System Events" to sleep')
            return "Mac going to sleep."
        return "Sleep initiated."
    elif action == "uptime":
        try:
            res = subprocess.run(["uptime"], capture_output=True, text=True, timeout=5)
            return f"System Uptime: {res.stdout.strip()}"
        except Exception as e:
            return f"Uptime query failed: {e}"
    return f"Unknown power action: {action}"


# ── Multi-tool declarations (auto-discovered by core/action_loader.py) ───────
TOOLS = [
    {
        "name": "get_battery_status",
        "description": "Checks the system battery percentage, charging state, and power source.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": get_battery_status,
    },
    {
        "name": "get_network_info",
        "description": "Gets current network connection details including Wi-Fi SSID, local IP address, and public IP.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": get_network_info,
    },
    {
        "name": "get_active_window",
        "description": "Returns the name and title of the currently focused/active application window on screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": get_active_window,
    },
    {
        "name": "toggle_do_not_disturb",
        "description": "Turns macOS Do Not Disturb / Focus mode on or off.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "enable": {
                    "type": "BOOLEAN",
                    "description": "True to enable Do Not Disturb, False to disable."
                }
            },
            "required": ["enable"]
        },
        "handler": toggle_do_not_disturb,
    },
    {
        "name": "get_clipboard_text",
        "description": "Reads and returns the current text stored in the system clipboard.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": get_clipboard_text,
    },
    {
        "name": "copy_to_clipboard",
        "description": "Copies text directly into the system clipboard.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text": {
                    "type": "STRING",
                    "description": "The exact text to place in clipboard."
                }
            },
            "required": ["text"]
        },
        "handler": copy_to_clipboard,
    },
    {
        "name": "empty_trash",
        "description": "Empties the macOS trash bin hands-free.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": empty_trash,
    },
    {
        "name": "run_shell_command",
        "description": "Executes a shell/terminal command hands-free on the local system and returns stdout/stderr.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {
                    "type": "STRING",
                    "description": "The bash/zsh shell command line to execute."
                }
            },
            "required": ["command"]
        },
        "handler": run_shell_command,
    },
    {
        "name": "mac_power_control",
        "description": "Controls system power state: lock screen, sleep display, sleep mac, or get system uptime.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "One of: lock_screen | sleep_display | sleep_mac | uptime"
                }
            },
            "required": ["action"]
        },
        "handler": mac_power_control,
    }
]
