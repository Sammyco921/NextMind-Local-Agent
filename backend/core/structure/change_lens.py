from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from core.structure.change_store import ChangeRecord, ChangeStore


class ChangeLens:
    """Deterministic read-model over ChangeStore.

    Provides:
      - timeline: chronological list of recent changes
      - component_evolution: per-component change counts + first/last change
      - goal_evolution: per-goal change counts + affected files/components

    Purely descriptive. No ranking, scoring, prediction, or recommendations.
    """

    def __init__(self, store: ChangeStore | None = None) -> None:
        self._store = store

    def timeline(self, count: int = 50) -> List[Dict[str, Any]]:
        if self._store is None:
            return []
        return [r.to_dict() for r in self._store.get_timeline(count=count)]

    def component_evolution(self) -> List[Dict[str, Any]]:
        if self._store is None:
            return []
        comps: Dict[Optional[str], Dict[str, Any]] = {}
        for r in self._store.get_all():
            key = r.component or "(none)"
            if key not in comps:
                comps[key] = {
                    "component": key,
                    "total_changes": 0,
                    "first_change": None,
                    "most_recent": None,
                    "action_types": defaultdict(int),
                    "goals": set(),
                }
            comps[key]["total_changes"] += 1
            comps[key]["first_change"] = (
                comps[key]["first_change"] or r.timestamp
            )
            comps[key]["most_recent"] = r.timestamp
            comps[key]["action_types"][r.action_type] += 1
            comps[key]["goals"].add(r.goal_id)

        result: List[Dict[str, Any]] = sorted(
            comps.values(),
            key=lambda c: c["total_changes"],
            reverse=True,
        )
        for c in result:
            c["action_types"] = dict(c["action_types"])
            c["goals"] = sorted(c["goals"])
        return result

    def goal_evolution(self) -> List[Dict[str, Any]]:
        if self._store is None:
            return []
        goals: Dict[str, Dict[str, Any]] = {}
        for r in self._store.get_all():
            if r.goal_id not in goals:
                goals[r.goal_id] = {
                    "goal_id": r.goal_id,
                    "goal_description": r.goal_description,
                    "files_changed": set(),
                    "components_changed": set(),
                    "timestamps": [],
                    "change_count": 0,
                    "action_types": defaultdict(int),
                }
            goals[r.goal_id]["files_changed"].add(r.file_path)
            if r.component:
                goals[r.goal_id]["components_changed"].add(r.component)
            goals[r.goal_id]["timestamps"].append(r.timestamp)
            goals[r.goal_id]["change_count"] += 1
            goals[r.goal_id]["action_types"][r.action_type] += 1

        result: List[Dict[str, Any]] = sorted(
            goals.values(),
            key=lambda g: g["change_count"],
            reverse=True,
        )
        for g in result:
            g["files_changed"] = sorted(g["files_changed"])
            g["components_changed"] = sorted(g["components_changed"])
            g["timestamps"] = sorted(g["timestamps"])
            g["action_types"] = dict(g["action_types"])
        return result
