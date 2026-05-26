# core/trace_store.py
#
# NextMind v0.8 — Trace Store
#
# Role:
#   Persistent execution trace collector for pipeline runs.
#
# Purpose:
#   - Store full execution history per run
#   - Enable debugging and replay
#   - Provide structured audit logs
#
# Non-goals:
#   - No memory / learning
#   - No analytics engine
#   - No optimization logic
#   - No semantic interpretation


from __future__ import annotations

from typing import Dict, Any, List, Optional
import json
import os
import time


# =====================================================
# TRACE STORE
# =====================================================

class TraceStore:
    """
    Simple filesystem-backed trace persistence layer.
    """

    def __init__(self, base_path: str = "state/traces"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    # =====================================================
    # SAVE RUN TRACE
    # =====================================================

    def save(self, run_id: str, trace: Dict[str, Any]) -> str:
        """
        Save full pipeline execution trace.
        """

        path = self._path(run_id)

        payload = {
            "run_id": run_id,
            "timestamp": time.time(),
            "trace": trace,
        }

        with open(path, "w") as f:
            json.dump(payload, f, indent=2)

        return path

    # =====================================================
    # LOAD TRACE
    # =====================================================

    def load(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Load previously saved trace.
        """

        path = self._path(run_id)

        if not os.path.exists(path):
            return None

        with open(path, "r") as f:
            return json.load(f)

    # =====================================================
    # LIST TRACES
    # =====================================================

    def list_traces(self) -> List[str]:
        """
        List all stored run IDs.
        """

        files = os.listdir(self.base_path)

        return [
            f.replace(".json", "")
            for f in files
            if f.endswith(".json")
        ]

    # =====================================================
    # DELETE TRACE
    # =====================================================

    def delete(self, run_id: str) -> bool:
        """
        Remove a stored trace.
        """

        path = self._path(run_id)

        if os.path.exists(path):
            os.remove(path)
            return True

        return False

    # =====================================================
    # INTERNAL HELPERS
    # =====================================================

    def _path(self, run_id: str) -> str:
        return os.path.join(self.base_path, f"{run_id}.json")