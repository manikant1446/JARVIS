"""
core/permissions.py — 4-Tier Security and Permission Architecture for MARK LIII.

Defines the permission hierarchy:
  LEVEL 0 — READ       : Information queries only (no system modifications).
  LEVEL 1 — SAFE       : Reversible local actions (execute immediately, register undo).
  LEVEL 2 — EXTERNAL   : Messages, email, external network submissions (confirmation required).
  LEVEL 3 — DESTRUCTIVE: Delete, shutdown, restart, empty trash, privileged shell (confirmation required).
"""
from __future__ import annotations

from enum import IntEnum
from typing import Callable, Optional
from core import confirm

class PermissionLevel(IntEnum):
    LEVEL_0_READ        = 0  # Info only
    LEVEL_1_SAFE        = 1  # Reversible local changes
    LEVEL_2_EXTERNAL    = 2  # Messages, email, external submissions
    LEVEL_3_DESTRUCTIVE = 3  # Delete, power, destructive shell

# Global trusted-send flags (can be configured via settings/config)
_TRUSTED_SEND_MESSAGE = False
_TRUSTED_SEND_EMAIL   = False


def set_trusted_send(messages: bool = False, emails: bool = False) -> None:
    global _TRUSTED_SEND_MESSAGE, _TRUSTED_SEND_EMAIL
    _TRUSTED_SEND_MESSAGE = messages
    _TRUSTED_SEND_EMAIL = emails


def is_trusted_send_messages() -> bool:
    return _TRUSTED_SEND_MESSAGE


def is_trusted_send_emails() -> bool:
    return _TRUSTED_SEND_EMAIL


def execute_with_permission(
    level: PermissionLevel,
    title: str,
    detail: str,
    action_fn: Callable[[], str],
    key: Optional[str] = None,
    trusted_override: bool = False,
) -> str:
    """
    Executes action_fn if permitted by level, or parks it behind the confirmation gate.
    Returns:
      - Execution result if executed immediately.
      - Confirmation pending instruction string if blocked for confirmation.
    """
    if level == PermissionLevel.LEVEL_0_READ or level == PermissionLevel.LEVEL_1_SAFE:
        return action_fn()

    if level == PermissionLevel.LEVEL_2_EXTERNAL:
        if trusted_override:
            return action_fn()
        # Confirmation required for external communications
        gate_key = key or f"external_{title}"
        return confirm.request(gate_key, title, detail, action_fn)

    if level == PermissionLevel.LEVEL_3_DESTRUCTIVE:
        # Destructive actions ALWAYS require confirmation unless explicit gate bypass
        gate_key = key or f"destructive_{title}"
        return confirm.request(gate_key, title, detail, action_fn)

    return action_fn()
