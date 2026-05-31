"""Safe degradation modes — observational only.

Modes are detected from failure patterns but NEVER change logic paths.
They only affect output completeness.
"""
from enum import Enum
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timezone


class DegradationMode(str, Enum):
    NORMAL = "normal"
    DEGRADED_CONTEXT = "degraded_context"
    DEGRADED_EXECUTION = "degraded_execution"
    SAFE_MODE = "safe_mode"


CONTEXT_SOURCES = {
    "memory_store", "decision_store", "feedback_store", "goal_registry",
    "context_weighting", "context_synthesizer", "project_view",
    "continuity", "structure_lens", "relationship_lens", "change_lens",
    "activity_lens",
}

EXECUTION_SOURCES = {
    "dag_executor", "tool_registry", "pipeline",
}


@dataclass
class DegradationTracker:
    max_recent_failures: int = 5
    recent: deque = field(default_factory=lambda: deque(maxlen=10))

    def record(self, source_layer: str) -> None:
        self.recent.append({
            "source": source_layer,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    @property
    def current_mode(self) -> DegradationMode:
        if not self.recent:
            return DegradationMode.NORMAL
        context_failures = sum(
            1 for r in self.recent if r["source"] in CONTEXT_SOURCES
        )
        execution_failures = sum(
            1 for r in self.recent if r["source"] in EXECUTION_SOURCES
        )
        if execution_failures >= self.max_recent_failures:
            return DegradationMode.SAFE_MODE
        if execution_failures > 0:
            return DegradationMode.DEGRADED_EXECUTION
        if context_failures > 0:
            return DegradationMode.DEGRADED_CONTEXT
        return DegradationMode.NORMAL

    def to_dict(self) -> dict:
        return {
            "mode": self.current_mode.value,
            "recent_failures": len(self.recent),
        }


# Singleton — shared across the process
_global_tracker: DegradationTracker | None = None


def get_degradation_tracker() -> DegradationTracker:
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = DegradationTracker()
    return _global_tracker
