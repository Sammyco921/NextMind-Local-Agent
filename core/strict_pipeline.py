# core/strict_pipeline.py
#
# v1.9.1: Intent → Normalization → Parsing → DAG → Validation → Execution → Evaluation

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.agent_types import EvaluationResult
from core.dag_executor import DAGExecutor
from core.dag_validator import DAGValidator
from core.evaluator import StrictEvaluator
from core.goal_fidelity_validator import GoalFidelityValidator
from core.pipeline_types import (
    FailureStage,
    PipelineFailure,
    PipelineResult,
    StageRecord,
)
from core.planning_pipeline import PlanningPipeline
from core.planning_types import PlanResult, StructuredStep
from core.tool_registry import ToolRegistry


class StrictPipeline:
    """Mandatory staged pipeline — no stage skipped or merged."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self._planner = PlanningPipeline(registry=None)
        self._dag_validator = DAGValidator(registry)
        self._fidelity = GoalFidelityValidator()
        self._executor = DAGExecutor(registry)
        self._evaluator = StrictEvaluator()

    def run(self, goal: str) -> PipelineResult:
        raw_goal = (goal or "").strip()
        stages: List[StageRecord] = []
        warnings: List[str] = []

        if not raw_goal:
            return self._fail(
                raw_goal,
                "normalization",
                "Empty goal",
                stages,
                recoverable=True,
            )

        plan_result = self._planner.plan(raw_goal)
        failed_plan_stage = plan_result.failure_stage

        if plan_result.status != "planned":
            stages.append(
                StageRecord(
                    stage=failed_plan_stage,
                    status="failed",
                    detail=plan_result.errors[0] if plan_result.errors else "Planning failed",
                )
            )
            return self._fail(
                raw_goal,
                failed_plan_stage,
                plan_result.errors[0] if plan_result.errors else "Planning failed",
                stages,
                plan=plan_result,
                context={"errors": plan_result.errors, "stage_hint": failed_plan_stage},
                recoverable=failed_plan_stage == "dag_construction",
            )

        stages.append(
            StageRecord(
                stage="parsing",
                status="ok",
                detail=f"structured={len(plan_result.structured_steps or [])}",
            )
        )
        stages.append(StageRecord(stage="dag_construction", status="ok", detail=""))

        warnings.extend(plan_result.errors)
        structured_steps: List[StructuredStep] = list(plan_result.structured_steps or [])
        dag = plan_result.dag
        spec = plan_result.goal_spec

        pre_errors: List[str] = []
        pre_errors.extend(self._fidelity.validate(spec, structured_steps, dag))
        structural = self._dag_validator.validate(dag)
        if structural["status"] != "valid":
            pre_errors.extend(structural.get("errors", []))

        stages.append(
            StageRecord(
                stage="pre_execution_validation",
                status="failed" if pre_errors else "ok",
                detail=f"errors={len(pre_errors)}",
            )
        )

        if pre_errors:
            return self._fail(
                raw_goal,
                "pre_execution_validation",
                pre_errors[0],
                stages,
                plan=plan_result,
                structured_steps=structured_steps,
                context={"errors": pre_errors},
                recoverable=True,
            )

        execution = self._executor.execute(dag, raw_goal)
        stages.append(
            StageRecord(
                stage="execution",
                status="ok" if execution.status == "success" else "failed",
                detail=execution.status,
            )
        )
        stages.append(StageRecord(stage="trace_collection", status="ok", detail=""))

        if execution.status != "success":
            return self._fail(
                raw_goal,
                "execution",
                f"Execution ended with status '{execution.status}'",
                stages,
                plan=plan_result,
                structured_steps=structured_steps,
                execution=execution,
                pre_passed=True,
                context={"trace": execution.to_dict()},
            )

        evaluation = self._evaluator.check(
            raw_goal,
            execution,
            dag,
            spec=spec,
            pre_validation_passed=True,
        )
        stages.append(
            StageRecord(
                stage="semantic_evaluation",
                status="ok" if evaluation.passed else "failed",
                detail=evaluation.status,
            )
        )

        if not evaluation.passed:
            return self._fail(
                raw_goal,
                "semantic_evaluation",
                evaluation.issues[0] if evaluation.issues else "Semantic check failed",
                stages,
                plan=plan_result,
                structured_steps=structured_steps,
                execution=execution,
                evaluation=evaluation,
                pre_passed=True,
                context={"issues": evaluation.issues},
            )

        return PipelineResult(
            goal=raw_goal,
            status="success",
            stages=stages,
            plan=plan_result,
            structured_steps=structured_steps,
            execution=execution,
            evaluation=evaluation,
            pre_execution_passed=True,
            warnings=warnings,
        )

    def _fail(
        self,
        goal: str,
        stage: FailureStage,
        reason: str,
        stages: List[StageRecord],
        *,
        plan: Optional[PlanResult] = None,
        structured_steps: Optional[List[StructuredStep]] = None,
        execution=None,
        evaluation: Optional[EvaluationResult] = None,
        pre_passed: bool = False,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = False,
        warnings: Optional[List[str]] = None,
    ) -> PipelineResult:
        all_reasons = [reason]
        if context and context.get("errors"):
            all_reasons = list(context["errors"])[:10]

        return PipelineResult(
            goal=goal,
            status="failed",
            failed_stage=stage,
            failure=PipelineFailure(
                stage=stage,
                reason=reason,
                reasons=all_reasons,
                recoverable=recoverable,
                context=context or {},
            ),
            stages=stages,
            plan=plan,
            structured_steps=structured_steps or [],
            execution=execution,
            evaluation=evaluation,
            pre_execution_passed=pre_passed,
            warnings=warnings or [],
        )


