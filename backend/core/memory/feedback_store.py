from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional


class FeedbackRecord:
    def __init__(
        self,
        goal_id: str,
        action: str,
        outcome: str,
        expected_outcome: str = "success",
        deviation_type: str = "none",
        severity: str = "low",
        reason_code: str | None = None,
        record_id: str | None = None,
        timestamp: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.record_id = record_id or uuid.uuid4().hex
        self.goal_id = goal_id
        self.timestamp = timestamp or now
        self.action = action
        self.outcome = outcome
        self.expected_outcome = expected_outcome
        self.deviation_type = deviation_type
        self.severity = severity
        self.reason_code = reason_code

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "goal_id": self.goal_id,
            "timestamp": self.timestamp,
            "action": self.action,
            "outcome": self.outcome,
            "expected_outcome": self.expected_outcome,
            "deviation_type": self.deviation_type,
            "severity": self.severity,
            "reason_code": self.reason_code,
        }


class FeedbackStore:
    def __init__(self, jsonl_path: str = "memory/feedback.jsonl") -> None:
        self._lock = threading.Lock()
        self._records: List[FeedbackRecord] = []
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
                    self._records.append(FeedbackRecord(
                        goal_id=data["goal_id"],
                        action=data.get("action", ""),
                        outcome=data.get("outcome", ""),
                        expected_outcome=data.get("expected_outcome", "success"),
                        deviation_type=data.get("deviation_type", "none"),
                        severity=data.get("severity", "low"),
                        reason_code=data.get("reason_code"),
                        record_id=data.get("record_id"),
                        timestamp=data.get("timestamp"),
                    ))

    def append_record(self, record: FeedbackRecord) -> None:
        with self._lock:
            self._records.append(record)
            with open(self._jsonl_path, "a") as f:
                f.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
                f.flush()

    def get_records(self, goal_id: str | None = None) -> List[FeedbackRecord]:
        with self._lock:
            result = list(self._records)
        if goal_id is not None:
            result = [r for r in result if r.goal_id == goal_id]
        return result

    def get_recent(self, limit: int = 100) -> List[FeedbackRecord]:
        with self._lock:
            return list(self._records[-limit:])

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            if os.path.exists(self._jsonl_path):
                open(self._jsonl_path, "w").close()
