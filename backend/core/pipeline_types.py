# core/pipeline_types.py
#
# v1.9.1 strict pipeline stage contracts.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from core.evaluator import EvaluationResult
from core.intent_clarifier import ClarificationRequest
from core.planning_types import PlanResult, StructuredStep
from core.types import ExecutionResult

PipelineStage = Literal[
    "intent_clarification",
    "intent_classification",
    "normalization",
    "parsing",
    "dag_construction",
    "pre_execution_validation",
    "execution",
    "trace_collection",
    "semantic_evaluation",
]

FailureStage = Literal[
    "intent_clarification",
    "normalization",
    "parsing",
    "dag_construction",
    "pre_execution_validation",
    "execution",
    "semantic_evaluation",
    "intent_classification",
]


@dataclass
class StageRecord:
    stage: PipelineStage
    status: Literal["ok", "failed", "skipped"]
    detail: str = ""


@dataclass
class PipelineFailure:
    stage: FailureStage
    reason: str
    reasons: List[str] = field(default_factory=list)
    recoverable: bool = False
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "reason": self.reason,
            "reasons": self.reasons,
            "recoverable": self.recoverable,
            "context": self.context,
        }


@dataclass
class PipelineResult:
    goal: str
    status: Literal["success", "failed", "clarification_required"]
    failed_stage: Optional[FailureStage] = None
    failure: Optional[PipelineFailure] = None
    clarification: Optional[ClarificationRequest] = None
    stages: List[StageRecord] = field(default_factory=list)
    plan: Optional[PlanResult] = None
    structured_steps: List[StructuredStep] = field(default_factory=list)
    execution: Optional[ExecutionResult] = None
    evaluation: Optional[EvaluationResult] = None
    pre_execution_passed: bool = False
    warnings: List[str] = field(default_factory=list)
    continuation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        result: dict = {
            "goal": self.goal,
            "status": self.status,
            "failed_stage": self.failed_stage,
            "failure": self.failure.to_dict() if self.failure else None,
            "pre_execution_passed": self.pre_execution_passed,
            "warnings": self.warnings,
            "stages": [
                {"stage": s.stage, "status": s.status, "detail": s.detail}
                for s in self.stages
            ],
        }
        if self.clarification:
            result["clarification"] = self.clarification.to_dict()
        if self.execution:
            result["execution"] = self.execution.to_dict()
        if self.evaluation:
            result["evaluation"] = {
                "status": self.evaluation.status,
                "issues": self.evaluation.issues,
                "missing_constraints": self.evaluation.missing_constraints,
            }
        if self.continuation:
            result["continuation"] = self.continuation
        return result
