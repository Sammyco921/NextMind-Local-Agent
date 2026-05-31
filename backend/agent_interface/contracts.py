from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

AmbiguityState = Literal[
    "resolved",
    "normalized",
    "requires_clarification",
    "mapped_to_existing_goal",
]

ExecutionModeStr = Literal["execute", "observe", "explain"]


@dataclass
class ContextScope:
    goal_id: Optional[str] = None
    time_window_seconds: Optional[int] = None


@dataclass
class InputContract:
    goal: str
    context_scope: Optional[ContextScope] = None
    mode: ExecutionModeStr = "execute"
    flags: Optional[Dict[str, bool]] = None


@dataclass
class OutputMeta:
    timing_ms: float = 0.0
    goal_id: str = ""
    mode: ExecutionModeStr = "execute"
    status: str = "unknown"
    ambiguity_state: AmbiguityState = "resolved"


@dataclass
class TraceOutput:
    summary: str = ""
    status_line: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class OutputContract:
    result: Dict[str, Any] = field(default_factory=dict)
    context: Optional[Dict[str, Any]] = None
    trace: Optional[TraceOutput] = None
    continuation: Optional[Dict[str, Any]] = None
    meta: OutputMeta = field(default_factory=OutputMeta)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "result": self.result,
            "meta": {
                "timing_ms": self.meta.timing_ms,
                "goal_id": self.meta.goal_id,
                "mode": self.meta.mode,
                "status": self.meta.status,
                "ambiguity_state": self.meta.ambiguity_state,
            },
        }
        if self.trace is not None:
            d["trace"] = {
                "summary": self.trace.summary,
                "status_line": self.trace.status_line,
                "steps": self.trace.steps,
            }
        if self.context is not None:
            d["context"] = self.context
        if self.continuation is not None:
            d["continuation"] = self.continuation
        return d
