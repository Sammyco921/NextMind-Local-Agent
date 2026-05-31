from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set


_CHANGE_ACTIONS = frozenset({"created", "modified", "deleted", "renamed"})


@dataclass
class ChangeRecord:
    change_id: str
    timestamp: str
    goal_id: str
    goal_description: str
    file_path: str
    component: Optional[str]
    action_type: str
    tool: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_id": self.change_id,
            "timestamp": self.timestamp,
            "goal_id": self.goal_id,
            "goal_description": self.goal_description,
            "file_path": self.file_path,
            "component": self.component,
            "action_type": self.action_type,
            "tool": self.tool,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ChangeRecord:
        return cls(
            change_id=d.get("change_id", ""),
            timestamp=d.get("timestamp", ""),
            goal_id=d.get("goal_id", ""),
            goal_description=d.get("goal_description", ""),
            file_path=d.get("file_path", ""),
            component=d.get("component"),
            action_type=d.get("action_type", "modified"),
            tool=d.get("tool", ""),
        )


class ChangeStore:
    """Append-only, restart-safe change history store.

    Records observed project modifications (created, modified, deleted, renamed).
    Only direct observations — no inferred changes, no dependencies, no semantics.
    """

    def __init__(self, jsonl_path: Optional[str] = None) -> None:
        self._records: List[ChangeRecord] = []
        self._jsonl_path = jsonl_path
        if jsonl_path and os.path.isfile(jsonl_path):
            self._load()

    def _load(self) -> None:
        self._records = []
        try:
            with open(self._jsonl_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self._records.append(ChangeRecord.from_dict(json.loads(line)))
        except (OSError, json.JSONDecodeError):
            self._records = []

    def _append(self, record: ChangeRecord) -> None:
        self._records.append(record)
        if self._jsonl_path:
            d = record.to_dict()
            os.makedirs(os.path.dirname(self._jsonl_path), exist_ok=True)
            with open(self._jsonl_path, "a") as f:
                f.write(json.dumps(d, sort_keys=True) + "\n")

    def record_change(
        self,
        goal_id: str,
        goal_description: str,
        file_path: str,
        action_type: str = "modified",
        component: Optional[str] = None,
        tool: str = "",
    ) -> ChangeRecord:
        if action_type not in _CHANGE_ACTIONS:
            action_type = "modified"
        record = ChangeRecord(
            change_id=uuid.uuid4().hex,
            timestamp=datetime.now(timezone.utc).isoformat(),
            goal_id=goal_id,
            goal_description=goal_description[:120],
            file_path=file_path,
            component=component,
            action_type=action_type,
            tool=tool,
        )
        self._append(record)
        return record

    def get_all(self) -> List[ChangeRecord]:
        return list(self._records)

    def get_by_goal(self, goal_id: str) -> List[ChangeRecord]:
        return [r for r in self._records if r.goal_id == goal_id]

    def get_by_component(self, component: str) -> List[ChangeRecord]:
        return [r for r in self._records if r.component == component]

    def get_by_file(self, file_path: str) -> List[ChangeRecord]:
        return [r for r in self._records if r.file_path == file_path]

    def get_timeline(self, count: int = 50) -> List[ChangeRecord]:
        sorted_records = sorted(
            self._records, key=lambda r: r.timestamp, reverse=True,
        )
        return sorted_records[:count]

    def get_components_affected(self) -> Set[Optional[str]]:
        return {r.component for r in self._records}

    def clear(self) -> None:
        self._records = []
        if self._jsonl_path and os.path.isfile(self._jsonl_path):
            try:
                os.remove(self._jsonl_path)
            except OSError:
                pass
