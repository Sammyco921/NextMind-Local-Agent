# core/planning_errors.py
#
# Structured planning failures — never raise raw ValueError to callers.

from __future__ import annotations

from typing import List

from core.dag_node import DAG, DAGNode
from core.planning_types import PlanResult, StructuredStep


PLANNING_ERROR_TOOL = "__planning_error__"


def structured_error_node(message: str, *, raw_goal: str = "", phase: str = "planning") -> DAGNode:
    return DAGNode(
        node_id="plan_error",
        tool_name=PLANNING_ERROR_TOOL,
        raw_args={
            "message": message or "Planning failed",
            "goal": raw_goal,
            "phase": phase,
        },
        dependencies=[],
        metadata={"error": True, "planning_failure": True},
    )


def structured_error_dag(message: str, *, raw_goal: str = "", phase: str = "planning") -> DAG:
    return DAG(nodes=[structured_error_node(message, raw_goal=raw_goal, phase=phase)])


def plan_failure(
    message: str,
    *,
    raw_goal: str = "",
    errors: List[str] | None = None,
    intent_type: str | None = None,
    stage: str = "parsing",
) -> PlanResult:
    err_list = list(errors) if errors else [message]
    return PlanResult(
        dag=structured_error_dag(message, raw_goal=raw_goal, phase=stage),
        status="planning_failed",
        errors=err_list,
        intent_type=intent_type,  # type: ignore[arg-type]
        step_count=0,
        failure_stage=stage,
    )


def steps_parse_failure(step_errors: List[str], *, raw_goal: str = "", stage: str = "parsing") -> PlanResult:
    combined = "; ".join(step_errors[:5])
    if len(step_errors) > 5:
        combined += f" (+{len(step_errors) - 5} more)"
    return plan_failure(
        f"Could not parse goal into atomic steps: {combined}",
        raw_goal=raw_goal,
        errors=step_errors,
        stage=stage,
    )


def empty_steps_failure(*, raw_goal: str = "", stage: str = "parsing") -> PlanResult:
    return plan_failure("No executable steps produced from goal", raw_goal=raw_goal, stage=stage)


def invalid_structured_steps(step_errors: List[str], *, raw_goal: str = "", stage: str = "parsing") -> PlanResult:
    return plan_failure(
        "Structured steps failed validation before DAG build",
        raw_goal=raw_goal,
        errors=step_errors,
        stage=stage,
    )
