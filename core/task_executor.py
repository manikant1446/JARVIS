"""
core/task_executor.py — Multi-Step Task Execution Engine for MARK LIII.

Executes structured multi-step tasks according to the protocol:
  Understand → Plan → Execute → Verify → Recover → Report

Key invariants:
  - Do NOT expose internal chain-of-thought to the user.
  - Only output short, clean progress indicators:
      "Downloading...", "Extracting...", "Opening VS Code...",
      "Installing dependencies...", "Running tests...", "Done."
  - Checks the global emergency stop flag before each step.
  - Verifies each step before moving to the next.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional
from actions import computer_control


@dataclass
class TaskStep:
    name: str                           # Short human readable step label (e.g. "Downloading...")
    action: Callable[[], tuple[bool, str]]  # Callable returning (success, message)
    verification: Optional[Callable[[], bool]] = None
    recovery: Optional[Callable[[], bool]] = None


class MultiStepTaskExecutor:
    """Executes a series of steps with verification, recovery, and emergency stop."""

    def __init__(self, task_name: str, steps: List[TaskStep], player=None, speak=None):
        self.task_name = task_name
        self.steps = steps
        self.player = player
        self.speak = speak

    def run(self) -> str:
        if computer_control.is_emergency_stopped():
            return "🛑 Cannot start task: Emergency stop is active."

        self._log(f"Starting task: {self.task_name} ({len(self.steps)} steps)")

        completed = 0
        for step in self.steps:
            # 1. Check emergency stop
            if computer_control.is_emergency_stopped():
                msg = f"🛑 Emergency Stop: Task '{self.task_name}' aborted at '{step.name}'."
                self._log(msg)
                return msg

            # 2. Show clean progress indicator
            self._log(step.name)
            if self.speak:
                # Speak short progress phrase
                try:
                    self.speak(step.name)
                except Exception:
                    pass

            # 3. Execute
            try:
                ok, err = step.action()
            except Exception as e:
                ok, err = False, str(e)

            # 4. Verify
            if ok and step.verification:
                try:
                    ok = step.verification()
                    if not ok:
                        err = "Verification failed."
                except Exception as e:
                    ok, err = False, f"Verification error: {e}"

            # 5. Recover if needed
            if not ok:
                if step.recovery:
                    self._log(f"Attempting recovery for '{step.name}'...")
                    try:
                        recovered = step.recovery()
                        if recovered:
                            ok = True
                    except Exception:
                        ok = False

                if not ok:
                    msg = f"❌ Task '{self.task_name}' failed at step '{step.name}': {err}"
                    self._log(msg)
                    return msg

            completed += 1

        final_msg = "Done."
        self._log(final_msg)
        return f"Task '{self.task_name}' completed successfully ({completed}/{len(self.steps)} steps). Done."

    def _log(self, text: str) -> None:
        print(f"[TaskExecutor] {text}")
        if self.player:
            try:
                self.player.write_log(f"SYS: {text}")
            except Exception:
                pass


def request_emergency_stop() -> None:
    computer_control.emergency_stop()


def execute_task(title: str, steps: List[TaskStep], player=None, speak=None) -> str:
    executor = MultiStepTaskExecutor(title, steps, player=player, speak=speak)
    return executor.run()
