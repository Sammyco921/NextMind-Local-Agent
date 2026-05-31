from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.memory.context_synthesizer import ContextSnapshot, ContextSynthesizer
from core.memory.context_weighting import ContextWeightingSystem
from core.memory.decision_store import DecisionStore
from core.memory.execution_memory_store import ExecutionMemoryStore
from core.memory.goal_registry import GoalRegistry
from core.structure.change_store import ChangeStore
from core.structure.relationship_store import RelationshipStore
from core.workspace.activity_tracker import WorkspaceActivityTracker


class AgentContextAPI:
    """Read-only API layer exposing synthesized context to external agents.

    Thin wrapper over ContextSynthesizer — no logic, no state, no writes.
    This is the ONLY supported interface for agent-facing context retrieval.
    """

    def __init__(
        self,
        execution_store: ExecutionMemoryStore | None = None,
        decision_store: DecisionStore | None = None,
        goal_registry: GoalRegistry | None = None,
        weighting_system: ContextWeightingSystem | None = None,
        change_store: ChangeStore | None = None,
        relationship_store: RelationshipStore | None = None,
        activity_tracker: WorkspaceActivityTracker | None = None,
    ) -> None:
        self._synth = ContextSynthesizer(
            execution_store=execution_store,
            decision_store=decision_store,
            goal_registry=goal_registry,
            weighting_system=weighting_system,
            change_store=change_store,
            relationship_store=relationship_store,
            activity_tracker=activity_tracker,
        )

    def get_context(
        self,
        goal_ids: Optional[List[str]] = None,
        time_window_hours: int = 24,
    ) -> Dict[str, Any]:
        try:
            snapshot = self._synth.build_snapshot(
                goal_ids=goal_ids,
                time_window_hours=time_window_hours,
            )
        except Exception:
            snapshot = ContextSnapshot()

        return {
            "context": snapshot.to_dict(),
            "meta": {
                "goal_ids": goal_ids or [],
                "time_window_hours": time_window_hours,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    def get_goal_context(
        self,
        goal_id: str,
        time_window_hours: int = 24,
    ) -> Dict[str, Any]:
        return self.get_context(
            goal_ids=[goal_id],
            time_window_hours=time_window_hours,
        )

    def get_system_context(
        self,
        time_window_hours: int = 24,
    ) -> Dict[str, Any]:
        return self.get_context(
            goal_ids=None,
            time_window_hours=time_window_hours,
        )
