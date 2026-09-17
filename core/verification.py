"""
core/verification.py — Action Verification Engine for MARK LIII.

Ensures that actions claimed to have succeeded actually took effect:
  - File moved: verify presence at destination.
  - App opened: verify process/window exists.
  - Command: verify return code == 0.
  - Download: verify file exists and is non-empty.
"""
from __future__ import annotations

import os
import platform
import subprocess
import time
from pathlib import Path

_OS = platform.system()


def verify_file_exists(path: str | Path, min_size: int = 0) -> tuple[bool, str]:
    """Check if file exists and has at least min_size bytes."""
    p = Path(path).expanduser()
    if p.exists() and (min_size == 0 or p.stat().st_size >= min_size):
        return True, f"Verified: {p.name} exists ({p.stat().st_size} bytes)"
    return False, f"Verification failed: {p.name} does not exist or is too small"


def verify_file_moved(src: str | Path, dst: str | Path) -> tuple[bool, str]:
    """Check that destination exists and source is gone."""
    s = Path(src).expanduser()
    d = Path(dst).expanduser()
    if d.exists() and not s.exists():
        return True, f"Verified: {d.name} reached destination"
    return False, f"Verification failed: move incomplete (dst exists: {d.exists()}, src exists: {s.exists()})"


def verify_app_running(app_name: str) -> tuple[bool, str]:
    """Verify that an application process or window is running."""
    clean_name = app_name.lower().replace(".app", "").strip()
    is_running = False
    if _OS == "Darwin":
        try:
            res = subprocess.run(
                ["pgrep", "-if", clean_name],
                capture_output=True, text=True, timeout=3
            )
            if res.returncode == 0 and res.stdout.strip():
                is_running = True
            else:
                script = f'tell application "System Events" to (name of processes) contains "{app_name}"'
                as_res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
                is_running = "true" in as_res.stdout.lower()
        except Exception:
            is_running = False
    else:
        try:
            import psutil
            for p in psutil.process_iter(["name"]):
                if clean_name in (p.info.get("name") or "").lower():
                    is_running = True
                    break
        except Exception:
            pass

    if is_running:
        return True, f"Verified: {app_name} is running"
    return False, f"Verification failed: {app_name} is not running"


def verify_command_success(returncode: int, stderr: str = "") -> tuple[bool, str]:
    """Verify shell execution completed successfully."""
    if returncode == 0:
        return True, "Success (exit code 0)"
    err_snippet = stderr.strip()[:100] if stderr else f"Exit code {returncode}"
    return False, f"Failed: {err_snippet}"


def verify_url_reachable(url: str, timeout: float = 3.0) -> bool:
    """Verify an HTTP endpoint responds with a successful or redirect code."""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except Exception:
        return False
