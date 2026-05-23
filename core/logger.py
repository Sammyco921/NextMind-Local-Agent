import os
import json
from datetime import datetime


class Logger:

    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

        self.session_file = self._new_session_file()

    # ====================================================
    # SESSION MANAGEMENT
    # ====================================================

    def _new_session_file(self):
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.log_dir, f"session_{timestamp}.log")

    # ====================================================
    # CORE WRITE FUNCTION
    # ====================================================

    def _write(self, level: str, message: str, data=None):

        timestamp = datetime.utcnow().isoformat()

        entry = {
            "time": timestamp,
            "level": level,
            "message": message,
            "data": data
        }

        line = self._format(entry)

        with open(self.session_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    # ====================================================
    # FORMATTER
    # ====================================================

    def _format(self, entry: dict) -> str:

        base = f"[{entry['time']}] [{entry['level']}] {entry['message']}"

        if entry["data"] is not None:
            try:
                pretty = json.dumps(entry["data"], indent=2)
                return base + "\n" + pretty
            except Exception:
                return base + "\n" + str(entry["data"])

        return base

    # ====================================================
    # PUBLIC API
    # ====================================================

    def info(self, message, data=None):
        self._write("INFO", message, data)

    def debug(self, message, data=None):
        self._write("DEBUG", message, data)

    def warning(self, message, data=None):
        self._write("WARNING", message, data)

    def error(self, message, data=None):
        self._write("ERROR", message, data)

    def critical(self, message, data=None):
        self._write("CRITICAL", message, data)

    # ====================================================
    # SPECIALIZED LOGS (VERY USEFUL FOR AGENTS)
    # ====================================================

    def log_step(self, step: dict):
        self._write("STEP", "Planner step executed", step)

    def log_result(self, result: dict):
        self._write("RESULT", "Execution result", result)

    def log_failure(self, reason: str, data=None):
        self._write("FAILURE", reason, data)

    def log_success(self, message: str, data=None):
        self._write("SUCCESS", message, data)
