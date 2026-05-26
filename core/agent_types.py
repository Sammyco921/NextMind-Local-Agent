# core/agent_types.py
#
# v1.8 agent loop result types.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Literal, Optional

from core.types import ExecutionResult

AgentStatus = Literal[
    "success",
    "repair_exhausted",
    "planning_failed",
    "validation_failed",
]


@dataclass
class EvaluationResult:
    status: Literal["pass", "fail"]
    issues: List[str] = field(default_factory=list)
    missing_constraints: List[str] = field(default_factory=list)
    confidence: float = 1.0

    @property
    def passed(self) -> bool:
        return self.status == "pass"


@dataclass
class AgentRunResult:
    goal: str
    status: AgentStatus
    execution: Optional[ExecutionResult] = None
    evaluations: List[EvaluationResult] = field(default_factory=list)
    iterations: int = 0
    dag: Any = None
    repair_log: List[str] = field(default_factory=list)
    planning_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "status": self.status,
            "iterations": self.iterations,
            "repair_log": self.repair_log,
            "planning_errors": self.planning_errors,
            "evaluations": [
                {
                    "status": e.status,
                    "issues": e.issues,
                    "missing_constraints": e.missing_constraints,
                    "confidence": e.confidence,
                }
                for e in self.evaluations
            ],
            "execution": self.execution.to_dict() if self.execution else None,
        }
