# core/planning_types.py
#
# Structured planning IR (v1.7) — single contract between parser/decomposer and DAG builder.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from core.dag_node import DAG

IntentType = Literal["simple", "complex"]


class IntentClassification(TypedDict):
    type: IntentType
    raw_goal: str
    requires_decomposition: bool


class StructuredStep(TypedDict, total=False):
    """Atomic tool-level step; no natural language in final output."""

    id: str
    action: str
    tool: str
    args: Dict[str, Any]
    dependencies: List[str]
    metadata: Dict[str, Any]
    goal_step_index: int


@dataclass
class PlanResult:
    """
    Outcome of the unified planning pipeline.

    v1.8: plans are hypotheses — correctness is established only after
    execution + evaluation (and optional repair), not at plan time.
    """

    dag: Any  # core.dag_node.DAG — avoid import cycle at module load
    status: Literal["planned", "planning_failed"]
    errors: List[str] = field(default_factory=list)
    intent_type: Optional[IntentType] = None
    step_count: int = 0
    is_hypothesis: bool = True
    raw_goal: str = ""
    structured_steps: List[StructuredStep] = field(default_factory=list)
    goal_spec: Any = None
    failure_stage: str = "parsing"

    @property
    def ok(self) -> bool:
        return self.status == "planned" and not self.errors
