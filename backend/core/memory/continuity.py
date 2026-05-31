from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from core.memory.execution_memory_store import ExecutionMemoryStore
from core.memory.feedback_store import FeedbackStore
from core.memory.goal_registry import GoalRegistry


@dataclass(frozen=True)
class ContinuationResult:
    is_continuation: bool = False
    parent_goal_id: str | None = None
    parent_description: str | None = None
    continuation_reason: str | None = None
    candidate_goal_ids: tuple = ()

    def to_dict(self) -> dict:
        return {
            "is_continuation": self.is_continuation,
            "parent_goal_id": self.parent_goal_id,
            "parent_description": self.parent_description,
            "continuation_reason": self.continuation_reason,
            "candidate_goal_ids": list(self.candidate_goal_ids),
        }


def _jaccard_similarity(a: str, b: str) -> float:
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


class ContinuityDetector:
    def __init__(
        self,
        goal_registry: GoalRegistry | None = None,
        execution_store: ExecutionMemoryStore | None = None,
        feedback_store: FeedbackStore | None = None,
    ) -> None:
        self._goals = goal_registry
        self._execution = execution_store
        self._feedback = feedback_store

    def detect(self, goal_text: str) -> ContinuationResult:
        candidates: list = []

        if self._goals is not None:
            for g in self._goals.list_goals():
                if g.lifecycle_state not in ("failed", "blocked", "active"):
                    continue
                sim = _jaccard_similarity(goal_text, g.description)
                if sim >= 0.3:
                    candidates.append((sim, g.goal_id, g.description, g.lifecycle_state))

        if self._feedback is not None:
            for r in self._feedback.get_recent(limit=50):
                if r.outcome in ("failed", "blocked"):
                    sim = _jaccard_similarity(goal_text, r.action)
                    if sim >= 0.3:
                        gid = r.goal_id
                        desc = r.action
                        if not any(c[1] == gid for c in candidates):
                            candidates.append((sim, gid, desc, "failed"))

        candidates.sort(key=lambda x: x[0], reverse=True)

        if not candidates:
            return ContinuationResult()

        best_sim, best_id, best_desc, best_state = candidates[0]
        all_ids = tuple(c[1] for c in candidates)

        if best_state == "active":
            reason = "Continuing work on an active task"
        elif best_state == "failed":
            reason = "Previous attempt did not complete"
        elif best_state == "blocked":
            reason = "Continuing work that was blocked"
        else:
            reason = "Similar to previous work"

        return ContinuationResult(
            is_continuation=True,
            parent_goal_id=best_id,
            parent_description=best_desc,
            continuation_reason=reason,
            candidate_goal_ids=all_ids,
        )
