from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple, TypeVar

from core.memory.feedback_store import FeedbackStore

if TYPE_CHECKING:
    from core.memory.context_synthesizer import (
        ActiveGoalSnapshot,
        Blocker,
        DecisionSnapshot,
    )

T = TypeVar("T")


class SalienceLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class SignalWeights:
    recency: float = 0.30
    frequency: float = 0.20
    outcome_success: float = 0.20
    goal_relevance: float = 0.20
    failure_recurrence: float = 0.10

    def total_weight(self) -> float:
        return (
            self.recency
            + self.frequency
            + self.outcome_success
            + self.goal_relevance
            + self.failure_recurrence
        )


DEFAULT_WEIGHTS = SignalWeights()


class ContextWeightingSystem:
    def __init__(
        self,
        feedback_store: FeedbackStore | None = None,
        weights: SignalWeights | None = None,
    ) -> None:
        self._feedback = feedback_store
        self._weights = weights or DEFAULT_WEIGHTS

    def compute_recency_score(
        self,
        timestamp_str: str | None,
        now: datetime | None = None,
    ) -> float:
        if timestamp_str is None:
            return 0.0
        try:
            ts = datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError):
            return 0.0
        now = now or datetime.now(timezone.utc)
        hours_since = max(0.0, (now - ts).total_seconds() / 3600.0)
        return self._weights.recency * (2.0 / (1.0 + hours_since / 24.0))

    def compute_goal_relevance_score(
        self, item_goal_id: str, query_goal_id: str | None
    ) -> float:
        if query_goal_id is None:
            return self._weights.goal_relevance
        if item_goal_id == query_goal_id:
            return self._weights.goal_relevance
        return 0.0

    def compute_outcome_score(self, goal_id: str) -> float:
        if self._feedback is None:
            return 0.0
        records = self._feedback.get_records(goal_id=goal_id)
        if not records:
            return 0.0
        successes = sum(1 for r in records if r.outcome == "success")
        total = len(records)
        return self._weights.outcome_success * (successes / max(1.0, float(total)))

    def compute_failure_recurrence(self, goal_id: str) -> float:
        if self._feedback is None:
            return 0.0
        records = self._feedback.get_records(goal_id=goal_id)
        if not records:
            return 0.0
        failures = sum(1 for r in records if r.outcome in ("failed", "blocked"))
        return self._weights.failure_recurrence * min(1.0, failures / 5.0)

    def compute_frequency_score(
        self, items: List[DecisionSnapshot], goal_id: str
    ) -> float:
        if not items:
            return 0.0
        count = sum(1 for d in items if d.goal_id == goal_id)
        return self._weights.frequency * min(1.0, count / 10.0)

    def score_decision(
        self,
        decision: DecisionSnapshot,
        query_goal_id: str | None = None,
        all_decisions: List[DecisionSnapshot] | None = None,
        timestamp_str: str | None = None,
        now: datetime | None = None,
    ) -> float:
        recency = self.compute_recency_score(timestamp_str, now=now)
        relevance = self.compute_goal_relevance_score(decision.goal_id, query_goal_id)
        outcome = self.compute_outcome_score(decision.goal_id)
        failure = self.compute_failure_recurrence(decision.goal_id)
        freq = (
            self.compute_frequency_score(all_decisions, decision.goal_id)
            if all_decisions
            else 0.0
        )
        return recency + relevance + outcome + failure + freq

    def score_active_goal(
        self,
        goal: ActiveGoalSnapshot,
        query_goal_id: str | None = None,
    ) -> float:
        relevance = self.compute_goal_relevance_score(goal.goal_id, query_goal_id)
        outcome = self.compute_outcome_score(goal.goal_id)
        failure = self.compute_failure_recurrence(goal.goal_id)
        return relevance + outcome + failure

    def score_blocker(
        self,
        blocker: Blocker,
        query_goal_id: str | None = None,
    ) -> float:
        relevance = self.compute_goal_relevance_score(blocker.goal_id, query_goal_id)
        failure = self.compute_failure_recurrence(blocker.goal_id)
        if failure > 0:
            failure += self._weights.outcome_success
        return relevance + failure

    @staticmethod
    def classify_salience(score: float) -> SalienceLevel:
        if score >= 0.5:
            return SalienceLevel.HIGH
        elif score >= 0.2:
            return SalienceLevel.MEDIUM
        return SalienceLevel.LOW

    @staticmethod
    def compress_by_salience(
        items: List[T],
        scorer_fn: Callable[[T], float],
        max_items: int = 20,
    ) -> List[T]:
        if len(items) <= max_items:
            scored = [(scorer_fn(item), item) for item in items]
            scored.sort(key=lambda x: x[0], reverse=True)
            return [item for _, item in scored]
        scored: List[Tuple[float, T]] = [(scorer_fn(item), item) for item in items]
        scored.sort(key=lambda x: x[0], reverse=True)
        high: List[T] = []
        medium: List[T] = []
        low: List[T] = []
        for score, item in scored:
            level = ContextWeightingSystem.classify_salience(score)
            if level == SalienceLevel.HIGH:
                high.append(item)
            elif level == SalienceLevel.MEDIUM:
                medium.append(item)
            else:
                low.append(item)
        result = high + medium
        remaining = max_items - len(result)
        if remaining > 0 and low:
            result.extend(low[:remaining])
        return result[:max_items]
