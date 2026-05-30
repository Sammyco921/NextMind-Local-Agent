from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from core.memory.context_weighting import ContextWeightingSystem, SalienceLevel
from core.memory.decision_store import Decision, DecisionStore
from core.memory.execution_memory_store import ExecutionMemoryStore
from core.memory.goal_registry import GoalRegistry


@dataclass(frozen=True)
class ActiveGoalSnapshot:
    goal_id: str
    description: str
    status: str
    blockers: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class DecisionSnapshot:
    goal_id: str
    decision_point: str
    rationale: str | None
    selected: str
    alternatives: List[str] = field(default_factory=list)
    timestamp: str = ""


@dataclass(frozen=True)
class NodeOutcome:
    node_id: str
    status: str


@dataclass(frozen=True)
class FailureSummary:
    node_id: str
    error: str
    count: int


@dataclass(frozen=True)
class ExecutionSummary:
    recent_nodes: List[NodeOutcome] = field(default_factory=list)
    failures: List[FailureSummary] = field(default_factory=list)


@dataclass(frozen=True)
class Blocker:
    goal_id: str
    reason: str


@dataclass(frozen=True)
class ContextSnapshot:
    active_goals: List[ActiveGoalSnapshot] = field(default_factory=list)
    relevant_decisions: List[DecisionSnapshot] = field(default_factory=list)
    execution_summary: ExecutionSummary = field(default_factory=ExecutionSummary)
    blockers: List[Blocker] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "active_goals": [
                {"goal_id": g.goal_id, "description": g.description,
                 "status": g.status, "blockers": g.blockers}
                for g in self.active_goals
            ],
            "relevant_decisions": [
                {"goal_id": d.goal_id, "decision_point": d.decision_point,
                 "rationale": d.rationale, "selected": d.selected,
                 "alternatives": d.alternatives, "timestamp": d.timestamp}
                for d in self.relevant_decisions
            ],
            "execution_summary": {
                "recent_nodes": [
                    {"node_id": n.node_id, "status": n.status}
                    for n in self.execution_summary.recent_nodes
                ],
                "failures": [
                    {"node_id": f.node_id, "error": f.error, "count": f.count}
                    for f in self.execution_summary.failures
                ],
            },
            "blockers": [
                {"goal_id": b.goal_id, "reason": b.reason}
                for b in self.blockers
            ],
        }


class ContextSynthesizer:
    def __init__(
        self,
        execution_store: ExecutionMemoryStore | None = None,
        decision_store: DecisionStore | None = None,
        goal_registry: GoalRegistry | None = None,
        weighting_system: ContextWeightingSystem | None = None,
    ) -> None:
        self._execution = execution_store
        self._decisions = decision_store
        self._goals = goal_registry
        self._weighting = weighting_system

    def build_snapshot(
        self,
        goal_ids: Optional[List[str]] = None,
        time_window_hours: int = 24,
    ) -> ContextSnapshot:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
        active = self._build_active_goals(goal_ids)
        decisions = self._build_decisions(goal_ids, cutoff)
        exec_summary = self._build_execution_summary(cutoff)
        blockers = self._build_blockers(active, exec_summary, goal_ids)

        return ContextSnapshot(
            active_goals=active,
            relevant_decisions=decisions,
            execution_summary=exec_summary,
            blockers=blockers,
        )

    def _build_active_goals(
        self, goal_ids: Optional[List[str]] = None,
    ) -> List[ActiveGoalSnapshot]:
        if self._goals is None:
            return []
        all_goals = self._goals.list_goals()
        result: List[ActiveGoalSnapshot] = []
        for g in all_goals:
            if goal_ids is not None and g.goal_id not in goal_ids:
                continue
            if g.lifecycle_state not in ("active", "blocked"):
                continue
            result.append(ActiveGoalSnapshot(
                goal_id=g.goal_id,
                description=g.description,
                status=g.lifecycle_state,
            ))
        result.sort(key=lambda x: x.goal_id)
        if self._weighting is not None:
            query_gid = goal_ids[0] if goal_ids and len(goal_ids) == 1 else None
            scored = sorted(
                ((self._weighting.score_active_goal(g, query_goal_id=query_gid), g) for g in result),
                key=lambda x: x[0],
                reverse=True,
            )
            if len(scored) > 10:
                high: list = []
                medium: list = []
                low: list = []
                for score, g in scored:
                    level = self._weighting.classify_salience(score)
                    if level == SalienceLevel.HIGH:
                        high.append(g)
                    elif level == SalienceLevel.MEDIUM:
                        medium.append(g)
                    else:
                        low.append(g)
                result = high + medium
                remaining = 10 - len(result)
                if remaining > 0 and low:
                    result.extend(low[:remaining])
            else:
                result = [g for _, g in scored]
        return result

    def _build_decisions(
        self,
        goal_ids: Optional[List[str]],
        cutoff: datetime,
    ) -> List[DecisionSnapshot]:
        if self._decisions is None:
            return []
        raw = self._decisions.get_decisions()
        filtered: List[Decision] = []
        for d in raw:
            if goal_ids is not None and d.goal_id not in goal_ids:
                continue
            try:
                ts = datetime.fromisoformat(d.timestamp)
                if ts < cutoff:
                    continue
            except (ValueError, TypeError):
                continue
            filtered.append(d)

        dedup: Dict[str, Decision] = {}
        for d in filtered:
            key = f"{d.goal_id}:{d.decision_type}"
            existing = dedup.get(key)
            if existing is None or d.timestamp > existing.timestamp:
                dedup[key] = d

        result = [
            DecisionSnapshot(
                goal_id=d.goal_id,
                decision_point=d.decision_type,
                rationale=d.rationale,
                selected=d.description,
                alternatives=list(d.alternatives),
                timestamp=d.timestamp,
            )
            for d in sorted(dedup.values(), key=lambda x: x.timestamp)
        ]
        if self._weighting is not None:
            query_gid = goal_ids[0] if goal_ids and len(goal_ids) == 1 else None
            scored = sorted(
                (
                    (self._weighting.score_decision(
                        decision=ds,
                        query_goal_id=query_gid,
                        all_decisions=result,
                        timestamp_str=ds.timestamp,
                    ), ds)
                    for ds in result
                ),
                key=lambda x: x[0],
                reverse=True,
            )
            if len(scored) > 20:
                high: list = []
                medium: list = []
                low: list = []
                for score, ds in scored:
                    level = self._weighting.classify_salience(score)
                    if level == SalienceLevel.HIGH:
                        high.append(ds)
                    elif level == SalienceLevel.MEDIUM:
                        medium.append(ds)
                    else:
                        low.append(ds)
                result = high + medium
                remaining = 20 - len(result)
                if remaining > 0 and low:
                    result.extend(low[:remaining])
            else:
                result = [ds for _, ds in scored]
        return result

    def _build_execution_summary(
        self, cutoff: datetime,
    ) -> ExecutionSummary:
        if self._execution is None:
            return ExecutionSummary()

        events = self._execution.get_events()
        recent: List[Dict] = []
        for ev in events:
            try:
                ts = datetime.fromisoformat(ev.get("timestamp", ""))
                if ts >= cutoff:
                    recent.append(ev)
            except (ValueError, TypeError):
                continue

        last_per_node: Dict[str, str] = {}
        for ev in recent:
            sid = ev.get("node_id", "")
            st = ev.get("status", "")
            last_per_node[sid] = st

        node_outcomes = [
            NodeOutcome(node_id=nid, status=st)
            for nid, st in sorted(last_per_node.items())
        ]

        failures: Dict[str, List[str]] = {}
        for ev in recent:
            if ev.get("status") == "failed":
                msg = str(ev.get("error", "unknown"))
                failures.setdefault(msg, []).append(ev.get("node_id", "?"))

        failure_summary: List[FailureSummary] = []
        for msg, nodes in sorted(failures.items()):
            count = len(nodes)
            unique_nodes = sorted(set(nodes))
            for nid in unique_nodes:
                failure_summary.append(FailureSummary(
                    node_id=nid,
                    error=msg[:120],
                    count=max(1, count // len(unique_nodes)),
                ))

        collapsed: List[FailureSummary] = []
        seen: Dict[str, int] = {}
        for f in failure_summary:
            key = f"{f.node_id}:{f.error}"
            seen[key] = seen.get(key, 0) + f.count
        for key, total in sorted(seen.items()):
            nid, err = key.split(":", 1)
            collapsed.append(FailureSummary(
                node_id=nid,
                error=err,
                count=total,
            ))

        return ExecutionSummary(
            recent_nodes=node_outcomes,
            failures=collapsed,
        )

    def _build_blockers(
        self,
        active_goals: List[ActiveGoalSnapshot],
        exec_summary: ExecutionSummary,
        goal_ids: Optional[List[str]] = None,
    ) -> List[Blocker]:
        blockers: List[Blocker] = []

        for g in active_goals:
            if g.status == "blocked":
                blockers.append(Blocker(
                    goal_id=g.goal_id,
                    reason="Goal explicitly marked as blocked",
                ))

        if self._execution is None or self._goals is None:
            return blockers

        goals_by_desc: Dict[str, str] = {}
        for g in self._goals.list_goals():
            goals_by_desc[g.description] = g.goal_id

        events = self._execution.get_events()
        goal_last_status: Dict[str, str] = {}
        goal_latest_ts: Dict[str, str] = {}
        goal_latest_failures: Dict[str, str] = {}
        for ev in events:
            gid = str(ev.get("goal_id", ""))
            st = str(ev.get("status", ""))
            ts = str(ev.get("timestamp", ""))
            if goal_latest_ts.get(gid, "") < ts:
                goal_latest_ts[gid] = ts
                goal_last_status[gid] = st
                if st == "failed":
                    goal_latest_failures[gid] = str(ev.get("error", "unknown"))

        for exec_gid, st in goal_last_status.items():
            if st == "failed":
                matched_goal_id = goals_by_desc.get(exec_gid, exec_gid)
                is_already_blocked = any(
                    b.goal_id == matched_goal_id for b in blockers
                )
                if not is_already_blocked:
                    err = goal_latest_failures.get(exec_gid, "execution failed")
                    blockers.append(Blocker(
                        goal_id=matched_goal_id,
                        reason=f"Last execution attempt failed: {err[:120]}",
                    ))

        blockers.sort(key=lambda b: b.goal_id)
        if self._weighting is not None:
            query_gid = goal_ids[0] if goal_ids and len(goal_ids) == 1 else None
            scored = sorted(
                ((self._weighting.score_blocker(b, query_goal_id=query_gid), b) for b in blockers),
                key=lambda x: x[0],
                reverse=True,
            )
            if len(scored) > 10:
                high: list = []
                medium: list = []
                low: list = []
                for score, b in scored:
                    level = self._weighting.classify_salience(score)
                    if level == SalienceLevel.HIGH:
                        high.append(b)
                    elif level == SalienceLevel.MEDIUM:
                        medium.append(b)
                    else:
                        low.append(b)
                result = high + medium
                remaining = 10 - len(result)
                if remaining > 0 and low:
                    result.extend(low[:remaining])
            else:
                result = [b for _, b in scored]
            return result
        return blockers
