from __future__ import annotations

import json
import os
import threading
from typing import Dict, List


class ExecutionMemoryStore:
    """Append-only execution event store with JSONL persistence."""

    def __init__(self, jsonl_path: str = "memory/execution_events.jsonl") -> None:
        self._lock = threading.Lock()
        self._events: List[Dict] = []
        self._jsonl_path = jsonl_path
        os.makedirs(os.path.dirname(self._jsonl_path) or ".", exist_ok=True)
        self._load_existing()

    def _load_existing(self) -> None:
        if not os.path.exists(self._jsonl_path):
            return
        with open(self._jsonl_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    self._events.append(json.loads(line))

    def append_event(self, event: dict) -> None:
        with self._lock:
            self._events.append(event)
            with open(self._jsonl_path, "a") as f:
                f.write(json.dumps(event, sort_keys=True) + "\n")
                f.flush()

    def get_events(
        self,
        dag_id: str | None = None,
        goal_id: str | None = None,
    ) -> List[Dict]:
        with self._lock:
            result = list(self._events)
        if dag_id is not None:
            result = [e for e in result if e.get("dag_id") == dag_id]
        if goal_id is not None:
            result = [e for e in result if e.get("goal_id") == goal_id]
        return result

    def get_recent(self, limit: int = 100) -> List[Dict]:
        with self._lock:
            return list(self._events[-limit:])

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            if os.path.exists(self._jsonl_path):
                open(self._jsonl_path, "w").close()
