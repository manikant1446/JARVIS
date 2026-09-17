"""
core/feature_registry.py — Central registry of MARK LIII built-in capabilities.

This is a METADATA LAYER ONLY.  It does NOT replace, rewrite, or re-implement
any existing action module.  Each entry maps a human-readable capability name
to its availability flag and the file(s) that provide it.

The registry is consumed at startup to log integration health and can be
queried at runtime (e.g. "Mark, kaunsi features available hain?").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class FeatureInfo:
    """Metadata for one built-in capability."""
    enabled: bool = True
    providers: List[str] = field(default_factory=list)   # file(s) that implement it
    description: str = ""
    status: str = "ready"   # ready | degraded | unavailable


# ── Master registry ─────────────────────────────────────────────────────────
# Keys are stable identifiers used in logs and config; values carry metadata.
# The 'enabled' flag defaults to True — the feature is assumed present because
# the provider file ships with the project.  Runtime checks (API key missing,
# macOS-only on Windows, etc.) can flip a feature to 'degraded' or 'unavailable'
# without touching this dict — call mark_degraded() / mark_unavailable().

BUILT_IN_FEATURES: Dict[str, FeatureInfo] = {
    "system_control": FeatureInfo(
        providers=["system_control.py", "computer_settings.py"],
        description="Battery, WiFi, clipboard, DND, power, volume, brightness, lock screen",
    ),
    "computer_control": FeatureInfo(
        providers=["computer_control.py"],
        description="Mouse, keyboard, screenshot, OCR, UI element detection",
    ),
    "file_agent": FeatureInfo(
        providers=["file_controller.py", "file_processor.py"],
        description="File search, create, move, copy, rename, organize, PDF extraction",
    ),
    "browser_agent": FeatureInfo(
        providers=["browser_control.py"],
        description="Open website, web search, read page, tabs, forms, downloads",
    ),
    "music": FeatureInfo(
        providers=["music_control.py"],
        description="Play, pause, next, previous, volume, Spotify & Apple Music",
    ),
    "calendar": FeatureInfo(
        providers=["calendar_manager.py"],
        description="Today's schedule, upcoming events, create/update/delete events",
    ),
    "reminders": FeatureInfo(
        providers=["reminder.py", "calendar_manager.py"],
        description="Create, list, search, complete, update, delete reminders",
    ),
    "messaging": FeatureInfo(
        providers=["messaging_tools.py", "send_message.py"],
        description="iMessage, WhatsApp, FaceTime, audio calls, unread messages",
    ),
    "email": FeatureInfo(
        providers=["email_manager.py"],
        description="Unread emails, search, send, reply, attachment handling",
    ),
    "network_diagnostics": FeatureInfo(
        providers=["cybersec_tools.py"],
        description="Ping, DNS, WHOIS, IP info, port scan, traceroute, security audit",
    ),
    "productivity": FeatureInfo(
        providers=["productivity.py"],
        description="Pomodoro timer, focus mode, spotlight search",
    ),
    "morning_briefing": FeatureInfo(
        providers=["productivity.py", "main.py"],
        description="Auto daily briefing: time, weather, calendar, reminders, news",
    ),
    "live_information": FeatureInfo(
        providers=["information.py", "weather_report.py", "web_search.py"],
        description="Stocks, currency, cricket scores, Wikipedia, news, weather",
    ),
    "vision": FeatureInfo(
        providers=["screen_processor.py", "computer_control.py"],
        description="Screenshot analysis, OCR, screen understanding, code error analysis",
    ),
    "webcam_vision": FeatureInfo(
        providers=["screen_processor.py"],
        description="Webcam capture with explicit permission, visible camera status",
    ),
    "developer_mode": FeatureInfo(
        providers=["dev_tools.py", "dev_agent.py", "code_helper.py"],
        description="Terminal, Python execution, Git, VS Code, build, test, debug",
    ),
    "memory": FeatureInfo(
        providers=["memory_manager.py"],
        description="Save, retrieve, update, forget user preferences and context",
    ),
    "task_execution": FeatureInfo(
        providers=["task_executor.py"],
        description="Multi-step task pipeline: Understand -> Plan -> Execute -> Verify -> Recover -> Report",
    ),
    "command_router": FeatureInfo(
        providers=["command_router.py"],
        description="Central deterministic command router bypassing LLM for simple queries",
    ),
    "permissions": FeatureInfo(
        providers=["permissions.py", "confirm.py"],
        description="4-tier security system: Read, Safe, External (confirm), Destructive (confirm)",
    ),
    "verification": FeatureInfo(
        providers=["verification.py"],
        description="Post-action state verification: files, apps, commands, URLs",
    ),
    "automation": FeatureInfo(
        providers=["computer_control.py", "computer_settings.py"],
        description="Multi-step task execution, hotkeys, macros, emergency stop",
    ),
    "security": FeatureInfo(
        providers=["cybersec_tools.py", "system_control.py"],
        description="Network diagnostics, port inspection, connection monitoring, defensive tests",
    ),
    "web_search": FeatureInfo(
        providers=["web_search.py"],
        description="Google search, news, research, price comparison",
    ),
    "desktop": FeatureInfo(
        providers=["desktop.py"],
        description="Desktop management, wallpaper, organization",
    ),
}


def mark_degraded(feature_name: str, reason: str = "") -> None:
    """Mark a feature as degraded (partially working)."""
    feat = BUILT_IN_FEATURES.get(feature_name)
    if feat:
        feat.status = "degraded"


def mark_unavailable(feature_name: str, reason: str = "") -> None:
    """Mark a feature as unavailable."""
    feat = BUILT_IN_FEATURES.get(feature_name)
    if feat:
        feat.status = "unavailable"
        feat.enabled = False


def get_status_report() -> str:
    """Human-readable startup status block for logging."""
    lines = []
    for name, info in BUILT_IN_FEATURES.items():
        if info.status == "ready":
            icon = "✓"
        elif info.status == "degraded":
            icon = "⚠"
        else:
            icon = "✗"
        lines.append(f"  {icon} {name}")
    return "\n".join(lines)


def get_feature_list() -> list[dict]:
    """Compact list for tool responses — avoids sending the whole registry."""
    return [
        {"name": k, "enabled": v.enabled, "status": v.status}
        for k, v in BUILT_IN_FEATURES.items()
    ]
