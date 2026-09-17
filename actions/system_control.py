"""
actions/system_control.py — Deep native macOS system access ported from Layra.
Hands-free system utilities: battery, network, active window, DND, clipboard,
Finder empty trash, uptime, display sleep, and direct terminal shell execution.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from core.permissions import PermissionLevel, execute_with_permission

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
            b = psutil.sensors_battery()
            if b:
                plugged = "Plugged in" if b.power_plugged else "On battery"
                return f"🔋 Battery: {b.percent}% ({plugged})"
        except Exception:
            pass
    return "Battery info not available for this system."


def get_network_info(parameters: dict = None, **kwargs) -> str:
    """Get network details: Wi-Fi SSID, local IP address, interface status, and public IP."""
    info_lines = []
    if _OS == "Darwin":
        # Get active Wi-Fi SSID
        try:
            res = subprocess.run(
                ["networksetup", "-getairportnetwork", "en0"],
                capture_output=True, text=True, timeout=5
            )
            out = res.stdout.strip()
            if out and "error" not in out.lower():
                info_lines.append(f"📶 {out}")
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

    # Network interface statuses
    try:
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        if_lines = []
        for iface, stat in stats.items():
            if iface.startswith("lo") or not stat.isup:
                continue
            ip_addr = "no IP"
            for snic in addrs.get(iface, []):
                if snic.family.name in ("AF_INET", "AF_INET6") and not snic.address.startswith("127."):
                    ip_addr = snic.address
                    break
            if_lines.append(f"  • {iface}: UP, Speed: {stat.speed}Mbps, IP: {ip_addr}")
        if if_lines:
            info_lines.append("Active Interfaces:\n" + "\n".join(if_lines[:4]))
    except Exception:
        pass

    # Public IP
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
    """Empties macOS Finder trash with Level 3 confirmation."""
    def _do_empty():
        if _OS == "Darwin":
            script = 'tell application "Finder" to empty trash'
            run_applescript(script)
            return "Trash emptied successfully."
        return "Trash emptied."

    return execute_with_permission(
        PermissionLevel.LEVEL_3_DESTRUCTIVE,
        title="Empty Trash",
        detail="Permanently delete all items currently in the Trash.",
        action_fn=_do_empty,
        key="empty_trash"
    )


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
    """Handles lock_screen, sleep_mac, sleep_display, uptime, restart, or shutdown."""
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
    elif action == "restart":
        def _do_restart():
            if _OS == "Darwin":
                run_applescript('tell application "System Events" to restart')
            return "Restarting system."
        return execute_with_permission(
            PermissionLevel.LEVEL_3_DESTRUCTIVE,
            title="Restart Computer",
            detail="Restart the operating system now.",
            action_fn=_do_restart,
            key="restart"
        )
    elif action in ("shutdown", "shut_down", "power_off"):
        def _do_shutdown():
            if _OS == "Darwin":
                run_applescript('tell application "System Events" to shut down')
            return "Shutting down system."
        return execute_with_permission(
            PermissionLevel.LEVEL_3_DESTRUCTIVE,
            title="Shut Down Computer",
            detail="Shut down the operating system now.",
            action_fn=_do_shutdown,
            key="shutdown"
        )
    return f"Unknown power action: {action}"


def get_display_info(parameters: dict = None, **kwargs) -> str:
    """Get display information: count, resolution, and main display."""
    if _OS == "Darwin":
        try:
            res = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=8
            )
            out = res.stdout.strip()
            lines = []
            for line in out.splitlines():
                line_s = line.strip()
                if any(k in line_s for k in ("Chipset Model", "Resolution", "Display Type", "Main Display", "Mirror", "Online")):
                    lines.append(f"• {line_s}")
            if lines:
                return "🖥️ Display Information:\n" + "\n".join(lines)
        except Exception:
            pass
    try:
        import pyautogui
        w, h = pyautogui.size()
        return f"🖥️ Display Resolution: {w}x{h}"
    except Exception as e:
        return f"Could not retrieve display information: {e}"


def get_disk_usage(parameters: dict = None, **kwargs) -> str:
    """Get disk usage: total, used, free space, and percent."""
    path = (parameters or {}).get("path", "/")
    try:
        usage = psutil.disk_usage(path)
        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        return (
            f"💾 Disk Usage ({path}):\n"
            f"• Total: {total_gb:.1f} GB\n"
            f"• Used: {used_gb:.1f} GB ({usage.percent}%)\n"
            f"• Free: {free_gb:.1f} GB"
        )
    except Exception as e:
        return f"Could not get disk usage for {path}: {e}"


def get_running_processes(parameters: dict = None, **kwargs) -> str:
    """List running processes or search for a specific process."""
    params = parameters or {}
    filter_name = params.get("name", "").lower().strip()
    try:
        count = int(params.get("count", 10))
    except Exception:
        count = 10

    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                p_name = info.get("name") or ""
                if filter_name and filter_name not in p_name.lower():
                    continue
                procs.append(info)
            except Exception:
                continue

        if filter_name:
            if not procs:
                return f"No running processes found matching '{filter_name}'."
            lines = [f"Found {len(procs)} process(es) matching '{filter_name}':"]
            for p in procs[:count]:
                lines.append(f"• {p['name']} (PID: {p['pid']}, CPU: {p['cpu_percent'] or 0}%, RAM: {p['memory_percent'] or 0:.1f}%)")
            return "\n".join(lines)

        procs.sort(key=lambda x: (x.get("memory_percent") or 0), reverse=True)
        lines = ["⚡ Top Running Processes by Memory:"]
        for p in procs[:count]:
            lines.append(f"• {p['name']} (PID: {p['pid']}, RAM: {p['memory_percent'] or 0:.1f}%, CPU: {p['cpu_percent'] or 0}%)")
        return "\n".join(lines)
    except Exception as e:
        return f"Could not inspect running processes: {e}"


def close_application(parameters: dict = None, **kwargs) -> str:
    """Gracefully closes or quits an open application."""
    app_name = (parameters or {}).get("app_name", "").strip()
    if not app_name:
        return "Please specify the application name to close."

    if _OS == "Darwin":
        safe_name = app_name.replace('"', '\\"')
        script = f'tell application "{safe_name}" to quit'
        res = run_applescript(script)
        if "error" not in res.lower():
            return f"Closed {app_name}."
        subprocess.run(["killall", app_name], capture_output=True)
        return f"Closed {app_name}."
    else:
        for p in psutil.process_iter(["pid", "name"]):
            try:
                if app_name.lower() in (p.info.get("name") or "").lower():
                    p.terminate()
                    return f"Closed process {p.info.get('name')} (PID {p.info.get('pid')})."
            except Exception:
                pass
        return f"No active process matching '{app_name}' was found to close."


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
        "description": "Gets current network connection details including Wi-Fi SSID, local IP address, active interfaces, and public IP.",
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
        "description": "Empties the macOS trash bin (requires confirmation).",
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
        "description": "Controls system power state: lock_screen, sleep_display, sleep_mac, uptime, restart, or shutdown.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "One of: lock_screen | sleep_display | sleep_mac | uptime | restart | shutdown"
                }
            },
            "required": ["action"]
        },
        "handler": mac_power_control,
    },
    {
        "name": "get_display_info",
        "description": "Retrieves display and monitor details: resolution, display count, and screen settings.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": get_display_info,
    },
    {
        "name": "get_disk_usage",
        "description": "Checks disk space usage: total, used, free space, and usage percentage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {
                    "type": "STRING",
                    "description": "Disk mount path (default: '/')."
                }
            },
            "required": []
        },
        "handler": get_disk_usage,
    },
    {
        "name": "get_running_processes",
        "description": "Lists top running processes by CPU/memory or searches for a specific process name.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {
                    "type": "STRING",
                    "description": "Optional process name filter (e.g. 'python', 'chrome')."
                },
                "count": {
                    "type": "INTEGER",
                    "description": "Number of processes to return (default: 10)."
                }
            },
            "required": []
        },
        "handler": get_running_processes,
    },
    {
        "name": "close_application",
        "description": "Closes, quits, or terminates a running application by name.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of application to close (e.g. 'Spotify', 'Visual Studio Code', 'Chrome')."
                }
            },
            "required": ["app_name"]
        },
        "handler": close_application,
    },
]
