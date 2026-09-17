"""
actions/dev_tools.py — Native Developer Mode tools for MARK LIII.
Supports: terminal command execution (with Level 3 gate for dangerous commands), Python sandbox execution,
Git operations (status, diff, log, commands), project code search, VS Code integration, and test runner.
"""
from __future__ import annotations

import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from core.permissions import PermissionLevel, execute_with_permission
from core.verification import verify_command_success

_OS = platform.system()

# Dangerous shell commands requiring Level 3 confirmation
_DANGEROUS_PATTERNS = [
    r"\brm\s+-[rf]+",
    r"\bsudo\b",
    r"\bdd\b",
    r"\bmkfs\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-[fdx]+\b",
    r"\bchmod\s+-R\s+777\b",
    r"\bchown\s+-R\b",
    r"\bkill\s+-9\s+1\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r":\(\)\s*\{\s*:\|:&\s*\};:",  # fork bomb
]


def _is_dangerous(command: str) -> bool:
    for pat in _DANGEROUS_PATTERNS:
        if re.search(pat, command, re.IGNORECASE):
            return True
    return False


def run_terminal_command(parameters: dict = None, **kwargs) -> str:
    """Executes a shell command. Destructive/privileged commands require confirmation."""
    params = parameters or {}
    command = params.get("command", "").strip()
    cwd = params.get("cwd", "").strip() or str(Path.cwd())

    if not command:
        return "Please specify a terminal command to run."

    target_cwd = Path(cwd).expanduser().resolve()
    if not target_cwd.exists() or not target_cwd.is_dir():
        target_cwd = Path.cwd()

    def _do_run() -> str:
        try:
            res = subprocess.run(
                command,
                shell=True,
                cwd=str(target_cwd),
                capture_output=True,
                text=True,
                timeout=45
            )
            out = res.stdout.strip()
            err = res.stderr.strip()
            ok, v_msg = verify_command_success(res.returncode, err)

            parts = []
            if out:
                parts.append(f"STDOUT:\n{out[:3000]}")
            if err:
                parts.append(f"STDERR:\n{err[:1500]}")
            if not parts:
                parts.append("Command executed with no output.")
            parts.append(f"\n[{v_msg}]")
            return "\n\n".join(parts)
        except subprocess.TimeoutExpired:
            return "Command timed out after 45 seconds."
        except Exception as e:
            return f"Terminal execution error: {e}"

    if _is_dangerous(command):
        return execute_with_permission(
            level=PermissionLevel.LEVEL_3_DESTRUCTIVE,
            title=f"Execute dangerous command",
            detail=f"Directory: {target_cwd}\nCommand: `{command}`",
            action_fn=_do_run
        )

    return _do_run()


def execute_python_code(parameters: dict = None, **kwargs) -> str:
    """Executes a snippet of Python code in a sandboxed subprocess and returns stdout/stderr."""
    code = (parameters or {}).get("code", "").strip()
    if not code:
        return "Please provide Python code to execute."

    try:
        res = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=25
        )
        out = res.stdout.strip()
        err = res.stderr.strip()
        ok, v_msg = verify_command_success(res.returncode, err)

        parts = []
        if out:
            parts.append(f"Output:\n{out[:3000]}")
        if err:
            parts.append(f"Error:\n{err[:1500]}")
        if not parts:
            parts.append("Python code executed with no output.")
        parts.append(f"\n[{v_msg}]")
        return "\n\n".join(parts)
    except subprocess.TimeoutExpired:
        return "Python execution timed out after 25s."
    except Exception as e:
        return f"Python execution error: {e}"


def git_status(parameters: dict = None, **kwargs) -> str:
    """Checks git repository status."""
    repo_path = (parameters or {}).get("repo_path", "").strip() or str(Path.cwd())
    try:
        res = subprocess.run(
            ["git", "status", "-s", "-b"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        if res.returncode != 0:
            return f"Not a git repository or git error: {res.stderr.strip()}"
        out = res.stdout.strip()
        return f"🌿 Git Status ({repo_path}):\n{out}" if out else "Working tree clean, nothing to commit."
    except Exception as e:
        return f"Git status failed: {e}"


def git_diff(parameters: dict = None, **kwargs) -> str:
    """Shows git diff of unstaged or staged changes."""
    params = parameters or {}
    repo_path = params.get("repo_path", "").strip() or str(Path.cwd())
    staged = params.get("staged", False)

    cmd = ["git", "diff", "--stat"]
    if staged:
        cmd.append("--staged")

    try:
        res = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        out = res.stdout.strip()
        return f"🌿 Git Diff ({'Staged' if staged else 'Unstaged'}):\n{out}" if out else "No changes detected."
    except Exception as e:
        return f"Git diff error: {e}"


def git_command(parameters: dict = None, **kwargs) -> str:
    """Runs a git command (log, branch, commit, push, pull, checkout)."""
    params = parameters or {}
    subcommand = params.get("command", "status").strip()
    repo_path = params.get("repo_path", "").strip() or str(Path.cwd())

    # Protect against destructive git resets
    if "reset --hard" in subcommand or "clean -fd" in subcommand:
        def _do_git():
            r = subprocess.run(f"git {subcommand}", shell=True, cwd=repo_path, capture_output=True, text=True)
            return r.stdout.strip() or r.stderr.strip()

        return execute_with_permission(
            level=PermissionLevel.LEVEL_3_DESTRUCTIVE,
            title="Execute destructive Git command",
            detail=f"git {subcommand} in {repo_path}",
            action_fn=_do_git
        )

    try:
        res = subprocess.run(
            f"git {subcommand}",
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=20
        )
        out = res.stdout.strip() or res.stderr.strip()
        return f"🌿 Git [{subcommand}]:\n{out[:3000]}" if out else f"Git command '{subcommand}' completed."
    except Exception as e:
        return f"Git command failed: {e}"


def project_search(parameters: dict = None, **kwargs) -> str:
    """Searches for code patterns, keywords, or function definitions across a project."""
    params = parameters or {}
    query = params.get("query", "").strip()
    path = params.get("path", "").strip() or str(Path.cwd())
    extension = params.get("extension", "").strip()

    if not query:
        return "Please specify a search query."

    target_dir = Path(path).expanduser().resolve()
    if not target_dir.exists():
        return f"Path not found: {path}"

    try:
        # ripgrep or grep
        cmd = ["grep", "-rnI", query, str(target_dir)]
        if extension:
            cmd = ["grep", "-rnI", f"--include=*{extension}", query, str(target_dir)]

        res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        lines = [l for l in res.stdout.splitlines() if not "/." in l and "node_modules" not in l and "__pycache__" not in l]
        if not lines:
            return f"No matches found for '{query}' in {target_dir.name}/"
        preview = lines[:20]
        return f"🔍 Search results for '{query}' ({len(lines)} matches):\n" + "\n".join(preview)
    except Exception as e:
        return f"Project search error: {e}"


def open_vscode(parameters: dict = None, **kwargs) -> str:
    """Opens a project or file in Visual Studio Code."""
    path = (parameters or {}).get("path", "").strip() or str(Path.cwd())
    resolved = str(Path(path).expanduser().resolve())
    try:
        subprocess.Popen(["code", resolved], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"💻 VS Code opened for: {resolved}"
    except Exception:
        # Fallback to macOS open -a
        if _OS == "Darwin":
            try:
                subprocess.run(["open", "-a", "Visual Studio Code", resolved])
                return f"💻 VS Code opened for: {resolved}"
            except Exception as e:
                return f"Could not launch VS Code: {e}"
        return "Could not launch VS Code. Please ensure 'code' CLI is installed."


def run_project_tests(parameters: dict = None, **kwargs) -> str:
    """Runs test suite (pytest, unittest, or npm test) in the specified directory."""
    path = (parameters or {}).get("path", "").strip() or str(Path.cwd())
    target_dir = Path(path).expanduser().resolve()

    # Detect test runner
    cmd = None
    if (target_dir / "package.json").exists():
        cmd = "npm test"
    elif (target_dir / "pytest.ini").exists() or any(target_dir.glob("test_*.py")):
        cmd = "pytest"
    else:
        cmd = f"{sys.executable} -m unittest discover"

    try:
        res = subprocess.run(cmd, shell=True, cwd=str(target_dir), capture_output=True, text=True, timeout=60)
        out = res.stdout.strip()
        err = res.stderr.strip()
        verdict = "✅ Tests Passed" if res.returncode == 0 else "❌ Tests Failed"
        summary = (out or err)[-2000:]
        return f"{verdict} ({cmd}):\n{summary}"
    except subprocess.TimeoutExpired:
        return f"Tests timed out after 60s in {target_dir.name}/"
    except Exception as e:
        return f"Failed to run tests: {e}"


# ── Multi-tool declarations (auto-discovered by core/action_loader.py) ───────
TOOLS = [
    {
        "name": "run_terminal_command",
        "description": "Executes shell commands in a given working directory. Destructive commands require confirmation.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {
                    "type": "STRING",
                    "description": "Shell command line to execute."
                },
                "cwd": {
                    "type": "STRING",
                    "description": "Optional working directory."
                }
            },
            "required": ["command"]
        },
        "handler": run_terminal_command,
    },
    {
        "name": "execute_python_code",
        "description": "Runs Python code in a sandboxed subprocess and returns standard output and errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "code": {
                    "type": "STRING",
                    "description": "Python code snippet to execute."
                }
            },
            "required": ["code"]
        },
        "handler": execute_python_code,
    },
    {
        "name": "git_status",
        "description": "Checks Git status of current or specified repository.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "repo_path": {
                    "type": "STRING",
                    "description": "Path to Git repository (defaults to current project)."
                }
            },
            "required": []
        },
        "handler": git_status,
    },
    {
        "name": "git_diff",
        "description": "Shows unstaged or staged Git diffs.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "repo_path": {
                    "type": "STRING",
                    "description": "Path to Git repository."
                },
                "staged": {
                    "type": "BOOLEAN",
                    "description": "Whether to view staged changes."
                }
            },
            "required": []
        },
        "handler": git_diff,
    },
    {
        "name": "git_command",
        "description": "Executes Git commands like log, branch, commit, push, pull. Destructive resets require confirmation.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {
                    "type": "STRING",
                    "description": "Git subcommand (e.g. 'log -n 5', 'branch', 'pull')."
                },
                "repo_path": {
                    "type": "STRING",
                    "description": "Path to Git repository."
                }
            },
            "required": ["command"]
        },
        "handler": git_command,
    },
    {
        "name": "project_search",
        "description": "Searches for code patterns, function names, or keywords across files in a project.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Keyword or symbol to search."
                },
                "path": {
                    "type": "STRING",
                    "description": "Directory to search in."
                },
                "extension": {
                    "type": "STRING",
                    "description": "Optional extension to filter (e.g. '.py', '.ts')."
                }
            },
            "required": ["query"]
        },
        "handler": project_search,
    },
    {
        "name": "open_vscode",
        "description": "Opens the specified directory or file in Visual Studio Code.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {
                    "type": "STRING",
                    "description": "Path to project folder or file."
                }
            },
            "required": []
        },
        "handler": open_vscode,
    },
    {
        "name": "run_project_tests",
        "description": "Runs automated tests in a project directory using pytest, unittest, or npm test.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {
                    "type": "STRING",
                    "description": "Project directory to run tests in."
                }
            },
            "required": []
        },
        "handler": run_project_tests,
    }
]
