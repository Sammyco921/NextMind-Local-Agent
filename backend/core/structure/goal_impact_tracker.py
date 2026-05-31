from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set


@dataclass
class ImpactRecord:
    goal_id: str
    goal_description: str
    file_path: str
    component: Optional[str]
    action: str
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "goal_description": self.goal_description,
            "file_path": self.file_path,
            "component": self.component,
            "action": self.action,
            "timestamp": self.timestamp or datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ImpactRecord:
        return cls(
            goal_id=d.get("goal_id", ""),
            goal_description=d.get("goal_description", ""),
            file_path=d.get("file_path", ""),
            component=d.get("component"),
            action=d.get("action", ""),
            timestamp=d.get("timestamp", ""),
        )


class GoalImpactTracker:
    """Observational linkage between goals and project structure.

    Records direct observations only:
    - If a file was written → store that file
    - If a directory was listed → store that directory

    Never infers secondary impact, dependencies, or architectural consequences.
    """

    def __init__(self, jsonl_path: Optional[str] = None) -> None:
        self._records: List[ImpactRecord] = []
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
                        self._records.append(ImpactRecord.from_dict(json.loads(line)))
        except (OSError, json.JSONDecodeError):
            self._records = []

    def _append(self, record: ImpactRecord) -> None:
        self._records.append(record)
        if self._jsonl_path:
            d = record.to_dict()
            d["timestamp"] = d["timestamp"] or datetime.now(timezone.utc).isoformat()
            os.makedirs(os.path.dirname(self._jsonl_path), exist_ok=True)
            with open(self._jsonl_path, "a") as f:
                f.write(json.dumps(d, sort_keys=True) + "\n")

    def record_impact(
        self,
        goal_id: str,
        goal_description: str,
        file_path: str,
        component: Optional[str] = None,
        action: str = "affected",
    ) -> None:
        record = ImpactRecord(
            goal_id=goal_id,
            goal_description=goal_description,
            file_path=file_path,
            component=component,
            action=action,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._append(record)

    def get_impacts_for_goal(self, goal_id: str) -> List[ImpactRecord]:
        return [r for r in self._records if r.goal_id == goal_id]

    def get_goals_for_file(self, file_path: str) -> List[ImpactRecord]:
        return [r for r in self._records if r.file_path == file_path]

    def get_goals_for_component(self, component: str) -> List[ImpactRecord]:
        return [r for r in self._records if r.component == component]

    def get_recent_activity(self, count: int = 20) -> List[ImpactRecord]:
        sorted_records = sorted(
            self._records, key=lambda r: r.timestamp, reverse=True,
        )
        return sorted_records[:count]

    def get_affected_files(self, goal_id: str) -> Set[str]:
        return {r.file_path for r in self.get_impacts_for_goal(goal_id)}

    def get_affected_components(self, goal_id: str) -> Set[Optional[str]]:
        return {r.component for r in self.get_impacts_for_goal(goal_id)}

    def clear(self) -> None:
        self._records = []
        if self._jsonl_path and os.path.isfile(self._jsonl_path):
            try:
                os.remove(self._jsonl_path)
            except OSError:
                pass
