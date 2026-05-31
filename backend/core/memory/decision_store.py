from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional


class Decision:
    def __init__(
        self,
        goal_id: str,
        decision_type: str,
        description: str,
        alternatives: Optional[List[str]] = None,
        rationale: str | None = None,
        decision_id: str | None = None,
        timestamp: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.decision_id = decision_id or uuid.uuid4().hex
        self.goal_id = goal_id
        self.timestamp = timestamp or now
        self.decision_type = decision_type
        self.description = description
        self.alternatives = alternatives or []
        self.rationale = rationale

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "goal_id": self.goal_id,
            "timestamp": self.timestamp,
            "decision_type": self.decision_type,
            "description": self.description,
            "alternatives": self.alternatives,
            "rationale": self.rationale,
        }


class DecisionStore:
    def __init__(self, jsonl_path: str = "memory/decisions.jsonl") -> None:
        self._lock = threading.Lock()
        self._decisions: List[Decision] = []
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
                    data = json.loads(line)
                    self._decisions.append(Decision(
                        goal_id=data["goal_id"],
                        decision_type=data["decision_type"],
                        description=data.get("description", ""),
                        alternatives=data.get("alternatives", []),
                        rationale=data.get("rationale"),
                        decision_id=data.get("decision_id"),
                        timestamp=data.get("timestamp"),
                    ))

    def append_decision(self, decision: Decision) -> None:
        with self._lock:
            self._decisions.append(decision)
            with open(self._jsonl_path, "a") as f:
                f.write(json.dumps(decision.to_dict(), sort_keys=True) + "\n")
                f.flush()

    def get_decisions(self, goal_id: str | None = None) -> List[Decision]:
        with self._lock:
            result = list(self._decisions)
        if goal_id is not None:
            result = [d for d in result if d.goal_id == goal_id]
        return result

    def get_recent(self, limit: int = 100) -> List[Decision]:
        with self._lock:
            return list(self._decisions[-limit:])

    def clear(self) -> None:
        with self._lock:
            self._decisions.clear()
            if os.path.exists(self._jsonl_path):
                open(self._jsonl_path, "w").close()
