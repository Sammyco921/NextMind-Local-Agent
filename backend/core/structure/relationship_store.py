from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class RelationshipRecord:
    timestamp: str
    goal_id: str
    goal_description: str
    artifacts: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "goal_id": self.goal_id,
            "goal_description": self.goal_description,
            "artifacts": sorted(self.artifacts),
            "components": sorted(self.components),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> RelationshipRecord:
        return cls(
            timestamp=d.get("timestamp", ""),
            goal_id=d.get("goal_id", ""),
            goal_description=d.get("goal_description", ""),
            artifacts=d.get("artifacts", []),
            components=d.get("components", []),
        )


class RelationshipStore:
    """Append-only, restart-safe store for observed co-occurrence relationships.

    Records which files and components were touched together by the same goal.
    Pure observation — no inference, no dependency analysis, no semantics.
    """

    def __init__(self, jsonl_path: Optional[str] = None) -> None:
        self._records: List[RelationshipRecord] = []
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
                        self._records.append(RelationshipRecord.from_dict(json.loads(line)))
        except (OSError, json.JSONDecodeError):
            self._records = []

    def _append(self, record: RelationshipRecord) -> None:
        self._records.append(record)
        if self._jsonl_path:
            d = record.to_dict()
            os.makedirs(os.path.dirname(self._jsonl_path), exist_ok=True)
            with open(self._jsonl_path, "a") as f:
                f.write(json.dumps(d, sort_keys=True) + "\n")

    def record_relationship(
        self,
        goal_id: str,
        goal_description: str,
        artifacts: Optional[List[str]] = None,
        components: Optional[List[str]] = None,
    ) -> RelationshipRecord:
        record = RelationshipRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            goal_id=goal_id,
            goal_description=goal_description[:120],
            artifacts=sorted(set(artifacts or [])),
            components=sorted(set(components or [])),
        )
        self._append(record)
        return record

    def get_all(self) -> List[RelationshipRecord]:
        return list(self._records)

    def get_by_goal(self, goal_id: str) -> List[RelationshipRecord]:
        return [r for r in self._records if r.goal_id == goal_id]

    def get_by_artifact(self, file_path: str) -> List[RelationshipRecord]:
        return [r for r in self._records if file_path in r.artifacts]

    def get_by_component(self, component: str) -> List[RelationshipRecord]:
        return [r for r in self._records if component in r.components]

    def clear(self) -> None:
        self._records = []
        if self._jsonl_path and os.path.isfile(self._jsonl_path):
            try:
                os.remove(self._jsonl_path)
            except OSError:
                pass
