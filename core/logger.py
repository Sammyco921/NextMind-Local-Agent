import os
import json
from datetime import datetime
from pathlib import Path


class Logger:
    """
    Simple structured logger for NextMind v0.4.

    Responsibilities:
    - Session-based logging
    - Planner / execution / error logs
    - State snapshots
    """

    def __init__(self, base_dir="logs"):
        self.base_dir = Path(base_dir)
        self.session_dir = None
        self.session_id = None

    # ====================================================
    # SESSION MANAGEMENT
    # ====================================================

    def start_session(self, goal: str):
        """
        Create a new logging session.
        """

        self.session_id = self._generate_session_id(goal)
        self.session_dir = self.base_dir / f"session_{self.session_id}"

        self.session_dir.mkdir(parents=True, exist_ok=True)

        # create files
        (self.session_dir / "planner.log").touch()
        (self.session_dir / "execution.log").touch()
        (self.session_dir / "errors.log").touch()

        self.log_event("session_start", {"goal": goal})

        return self.session_id

    # ====================================================
    # PLANNER LOG
    # ====================================================

    def log_planner(self, raw: str, parsed: dict = None):
        self._append(
            "planner.log",
            {
                "timestamp": self._now(),
                "raw": raw,
                "parsed": parsed
            }
        )

    # ====================================================
    # EXECUTION LOG
    # ====================================================

    def log_execution(self, step: dict, result: dict):
        self._append(
            "execution.log",
            {
                "timestamp": self._now(),
                "step": step,
                "result": result
            }
        )

    # ====================================================
    # ERROR LOG
    # ====================================================

    def log_error(self, error: str, context: dict = None):
        self._append(
            "errors.log",
            {
                "timestamp": self._now(),
                "error": error,
                "context": context or {}
            }
        )

    # ====================================================
    # GENERIC EVENT LOG
    # ====================================================

    def log_event(self, event_type: str, data: dict):
        self._append(
            "execution.log",
            {
                "timestamp": self._now(),
                "event": event_type,
                "data": data
            }
        )

    # ====================================================
    # STATE SNAPSHOT
    # ====================================================

    def save_state(self, state: dict):
        if not self.session_dir:
            return

        path = self.session_dir / "state.json"

        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    # ====================================================
    # INTERNAL HELPERS
    # ====================================================

    def _append(self, filename: str, data: dict):
        if not self.session_dir:
            return

        path = self.session_dir / filename

        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")

    def _generate_session_id(self, goal: str) -> str:
        base = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        short = abs(hash(goal)) % 10000
        return f"{base}_{short}"

    def _now(self):
        return datetime.utcnow().isoformat()
