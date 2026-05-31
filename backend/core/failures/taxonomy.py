from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


class FailureCategory(str, Enum):
    EXECUTION_FAILURE = "execution_failure"
    CONTEXT_FAILURE = "context_failure"
    WORKSPACE_FAILURE = "workspace_failure"
    API_FAILURE = "api_failure"
    UI_FAILURE = "ui_failure"
    INTERNAL_GUARD_FAILURE = "internal_guard_failure"
    UNKNOWN_FAILURE = "unknown_failure"


SOURCE_LAYER_NAMES = {
    "dag_executor", "tool_registry", "pipeline",
    "memory_store", "decision_store", "feedback_store", "goal_registry",
    "context_weighting", "context_synthesizer", "agent_context",
    "project_view", "continuity", "structure_lens", "relationship_lens",
    "change_lens", "activity_lens",
    "workspace_resolver", "workspace_gateway", "workspace_tracker",
    "session_store", "session_manager",
    "command_router", "handoff_builder",
    "api_server", "agent_interface",
    "unknown",
}


@dataclass
class FailureRecord:
    category: FailureCategory
    source_layer: str
    safe_message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    debug_payload: dict | None = None
    original_exception: str | None = None

    def to_dict(self) -> dict:
        d: dict = {
            "category": self.category.value,
            "source_layer": self.source_layer,
            "safe_message": self.safe_message,
        }
        if self.debug_payload is not None:
            d["debug"] = self.debug_payload
        return d

    @classmethod
    def unknown(cls, source: str = "unknown") -> "FailureRecord":
        return cls(
            category=FailureCategory.UNKNOWN_FAILURE,
            source_layer=source,
            safe_message="An unexpected issue occurred. The system has handled it and continues running.",
        )
