# core/dag_planner.py
#
# v1.7: DAG planner accepts structured steps only — no raw NL parsing.

from __future__ import annotations

from typing import List, Optional

from core.dag_builder import DAGBuilder
from core.dag_node import DAG
from core.planning_pipeline import PlanningPipeline
from core.planning_types import PlanResult, StructuredStep
from core.tool_registry import ToolRegistry


class DAGPlanner:
    """
    Deterministic structured-step → DAG planner.

    Natural-language goals must go through PlanningPipeline (intent → parse/decompose).
    This class only builds DAGs from structured decomposition output.
    """

    def __init__(self, registry: Optional[ToolRegistry] = None) -> None:
        self._builder = DAGBuilder()
        self._pipeline = PlanningPipeline(registry=registry)

    def plan(self, goal: str) -> DAG:
        """Plan from a natural-language goal via the v1.7 pipeline (never raises)."""
        result = self._pipeline.plan(goal)
        return result.dag

    def plan_with_result(self, goal: str) -> PlanResult:
        """Full planning outcome including errors and intent metadata."""
        return self._pipeline.plan(goal)

    def build_from_steps(self, steps: List[StructuredStep]) -> DAG:
        """Build DAG directly from structured decomposition (no NL parsing)."""
        return self._builder.build(steps)
