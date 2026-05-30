from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.memory.decision_store import DecisionStore
from core.memory.execution_memory_store import ExecutionMemoryStore
from core.memory.feedback_store import FeedbackStore
from core.memory.goal_registry import GoalRegistry


@dataclass(frozen=True)
class GoalSummary:
    goal_id: str
    description: str
    status: str


@dataclass(frozen=True)
class BlockedGoalSummary:
    goal_id: str
    description: str
    reason: str
    attempt_count: int


@dataclass(frozen=True)
class ContinuationLink:
    child_goal_id: str
    child_description: str
    parent_goal_id: str
    parent_description: str
    reason: str


@dataclass(frozen=True)
class FailurePattern:
    error: str
    count: int
    goal_ids: List[str]


@dataclass(frozen=True)
class HistoryEntry:
    type: str
    goal_id: str
    description: str
    detail: str
    timestamp: str


@dataclass(frozen=True)
class GoalChain:
    goals: List[GoalSummary]
    link_reason: str


@dataclass(frozen=True)
class AttemptGroup:
    goal_id: str
    description: str
    attempt_count: int
    last_status: str


class ProjectIntelligenceView:
    def __init__(
        self,
        goal_registry: GoalRegistry | None = None,
        decision_store: DecisionStore | None = None,
        execution_store: ExecutionMemoryStore | None = None,
        feedback_store: FeedbackStore | None = None,
    ) -> None:
        self._goals = goal_registry
        self._decisions = decision_store
        self._execution = execution_store
        self._feedback = feedback_store

    def overview(self) -> Dict[str, Any]:
        active: List[Dict[str, Any]] = []
        blocked: List[Dict[str, Any]] = []
        completed: List[Dict[str, Any]] = []

        if self._goals is not None:
            for g in self._goals.list_goals():
                entry = {"goal_id": g.goal_id, "description": g.description}
                if g.lifecycle_state == "active":
                    active.append(entry)
                elif g.lifecycle_state == "blocked":
                    blocked.append({**entry, "reason": "Goal blocked"})
                elif g.lifecycle_state == "completed":
                    completed.append(entry)

        if blocked and self._execution is not None:
            for b in blocked:
                last = self._last_execution_for_goal(b["goal_id"])
                if last and last.get("error"):
                    b["reason"] = str(last["error"])[:120]

        failure_patterns: List[Dict[str, Any]] = []
        if self._feedback is not None:
            error_counter: Dict[str, int] = {}
            reason_goal_ids: Dict[str, set] = {}
            for r in self._feedback.get_records():
                if r.outcome in ("failed", "blocked") and r.reason_code:
                    reason_goal_ids.setdefault(r.reason_code, set()).add(r.goal_id)
                    error_counter[r.reason_code] = error_counter.get(r.reason_code, 0) + 1
            for reason, count in sorted(error_counter.items(), key=lambda x: -x[1]):
                if count >= 2:
                    failure_patterns.append({
                        "error": reason,
                        "count": count,
                        "goal_ids": sorted(reason_goal_ids[reason]),
                    })

        if self._feedback is not None:
            for r in self._feedback.get_records():
                if r.outcome in ("failed", "blocked") and not r.reason_code:
                    key = r.action[:60]
                    reason_goal_ids.setdefault(key, set()).add(r.goal_id)
                    error_counter[key] = error_counter.get(key, 0) + 1
            seen_keys = {p["error"] for p in failure_patterns}
            for action_text, count in sorted(error_counter.items(), key=lambda x: -x[1]):
                if action_text not in seen_keys and count >= 2:
                    failure_patterns.append({
                        "error": action_text,
                        "count": count,
                        "goal_ids": sorted(reason_goal_ids[action_text]),
                    })

        continuations: List[Dict[str, Any]] = []
        if self._goals is not None:
            for g in self._goals.list_goals():
                if g.parent_id:
                    parent = self._goals.get_goal(g.parent_id)
                    continuations.append({
                        "child_goal_id": g.goal_id,
                        "child_description": g.description,
                        "parent_goal_id": g.parent_id,
                        "parent_description": parent.description if parent else "",
                        "reason": "Linked goal",
                    })

        return {
            "lens": "overview",
            "active_goals": active,
            "blocked_goals": blocked,
            "completed_goals": completed,
            "continuation_links": continuations,
            "recurring_failures": failure_patterns,
            "goal_count": {
                "active": len(active),
                "blocked": len(blocked),
                "completed": len(completed),
                "total": len(active) + len(blocked) + len(completed),
            },
        }

    def history(self) -> Dict[str, Any]:
        entries: List[Dict[str, Any]] = []

        if self._execution is not None:
            for ev in self._execution.get_events()[-100:]:
                entries.append({
                    "type": "execution",
                    "goal_id": str(ev.get("goal_id", "")),
                    "description": f"Executing {ev.get('tool', '?')}",
                    "detail": ev.get("status", ""),
                    "timestamp": str(ev.get("timestamp", "")),
                })

        if self._decisions is not None:
            for d in self._decisions.get_decisions()[-100:]:
                entries.append({
                    "type": "decision",
                    "goal_id": d.goal_id,
                    "description": d.description,
                    "detail": d.decision_type,
                    "timestamp": d.timestamp,
                })

        if self._feedback is not None:
            for r in self._feedback.get_records()[-100:]:
                entries.append({
                    "type": "feedback",
                    "goal_id": r.goal_id,
                    "description": f"Outcome: {r.outcome}",
                    "detail": r.reason_code or "",
                    "timestamp": r.timestamp,
                })

        entries.sort(key=lambda e: e.get("timestamp", ""))
        return {"lens": "history", "entries": entries[-200:]}

    def continuity(self) -> Dict[str, Any]:
        chains: List[Dict[str, Any]] = []
        attempt_groups: List[Dict[str, Any]] = []

        if self._goals is not None:
            all_goals = self._goals.list_goals()
            parent_map: Dict[str, List[GoalSummary]] = {}
            for g in all_goals:
                if g.parent_id:
                    parent_map.setdefault(g.parent_id, []).append(GoalSummary(
                        goal_id=g.goal_id, description=g.description, status=g.lifecycle_state,
                    ))

            for g in all_goals:
                children = parent_map.get(g.goal_id, [])
                if children:
                    chains.append({
                        "root": {
                            "goal_id": g.goal_id,
                            "description": g.description,
                            "status": g.lifecycle_state,
                        },
                        "children": [
                            {"goal_id": c.goal_id, "description": c.description, "status": c.status}
                            for c in children
                        ],
                        "link_reason": "Continued from parent",
                    })

        if self._feedback is not None:
            action_counts: Counter = Counter()
            action_last: Dict[str, str] = {}
            action_goals: Dict[str, str] = {}
            for r in self._feedback.get_records():
                key = r.action[:80]
                action_counts[key] += 1
                action_last[key] = r.outcome
                action_goals[key] = r.goal_id

            for action_text, count in action_counts.most_common():
                if count >= 2:
                    attempt_groups.append({
                        "description": action_text,
                        "attempt_count": count,
                        "last_status": action_last.get(action_text, "unknown"),
                        "goal_id": action_goals.get(action_text, ""),
                    })

        return {
            "lens": "continuity",
            "goal_chains": chains,
            "repeated_attempts": attempt_groups,
        }

    def _last_execution_for_goal(self, goal_id: str) -> Dict[str, Any] | None:
        if self._execution is None:
            return None
        best: Dict[str, Any] | None = None
        best_ts = ""
        for ev in self._execution.get_events():
            if str(ev.get("goal_id", "")) == goal_id:
                ts = str(ev.get("timestamp", ""))
                if ts > best_ts:
                    best_ts = ts
                    best = ev
        return best
