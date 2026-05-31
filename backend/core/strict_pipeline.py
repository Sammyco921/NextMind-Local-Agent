# core/strict_pipeline.py
#
# SYSTEM BOUNDARY: This is a deterministic execution engine. It does not model
# project intelligence, reasoning, autonomy, or planning beyond DAG construction.
# No governance, coherence, simulation, memory, or recovery systems exist.
#
# v1.9.1: Intent → Normalization → Parsing → DAG → Validation → Execution → Evaluation

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.evaluator import EvaluationResult
from core.dag_executor import DAGExecutor
from core.dag_validator import DAGValidator
from core.evaluator import StrictEvaluator
from core.execution_mode import ExecutionMode
from core.execution_spec import ExecutionSpec
from core.goal_fidelity_validator import GoalFidelityValidator
from core.human_normalizer import HumanNormalizer
from core.intent_clarifier import IntentClarifier, IntentStatus
from core.memory.continuity import ContinuityDetector, ContinuationResult
from core.memory.decision_store import Decision, DecisionStore
from core.memory.execution_memory_store import ExecutionMemoryStore
from core.memory.feedback_store import FeedbackRecord, FeedbackStore
from core.memory.goal_registry import GoalRegistry
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

    def __init__(
        self,
        registry: ToolRegistry,
        execution_memory: ExecutionMemoryStore | None = None,
        goal_registry: GoalRegistry | None = None,
        decision_store: DecisionStore | None = None,
        feedback_store: FeedbackStore | None = None,
        continuity_detector: ContinuityDetector | None = None,
    ) -> None:
        self.registry = registry
        self._clarifier = IntentClarifier()
        self._planner = PlanningPipeline(registry=None)
        self._dag_validator = DAGValidator(registry)
        self._fidelity = GoalFidelityValidator()
        self._executor = DAGExecutor(registry, execution_memory=execution_memory)
        self._evaluator = StrictEvaluator()
        self._goals = goal_registry
        self._decisions = decision_store
        self._feedback = feedback_store
        self._continuity = continuity_detector
        self._normalizer = HumanNormalizer()

    def _record_decision(
        self,
        goal_id: str,
        decision_type: str,
        description: str,
        alternatives: Optional[List[str]] = None,
        rationale: str | None = None,
    ) -> None:
        if self._decisions is None:
            return
        try:
            decision = Decision(
                goal_id=goal_id,
                decision_type=decision_type,
                description=description,
                alternatives=alternatives,
                rationale=rationale,
            )
            self._decisions.append_decision(decision)
        except Exception:
            pass

    def _update_goal_state(self, goal_id: str, state: str) -> None:
        if self._goals is None:
            return
        try:
            self._goals.update_state(goal_id, state)
        except Exception:
            pass

    def _emit_feedback(
        self,
        goal_id: str | None,
        action: str,
        outcome: str,
        deviation_type: str = "none",
        severity: str = "low",
        reason_code: str | None = None,
    ) -> None:
        if self._feedback is None:
            return
        try:
            record = FeedbackRecord(
                goal_id=goal_id or "",
                action=action,
                outcome=outcome,
                expected_outcome="success",
                deviation_type=deviation_type,
                severity=severity,
                reason_code=reason_code,
            )
            self._feedback.append_record(record)
        except Exception:
            pass

    def run(
        self,
        goal: str,
        mode: ExecutionMode | None = None,
    ) -> PipelineResult:
        raw_goal = (goal or "").strip()
        stages: List[StageRecord] = []
        warnings: List[str] = []

        if mode is None:
            mode = ExecutionMode.NORMAL

        spec = ExecutionSpec.for_mode(mode)

        if not raw_goal:
            self._emit_feedback(
                goal_id=None,
                action=raw_goal,
                outcome="aborted",
                deviation_type="aborted",
                severity="low",
                reason_code="empty_goal",
            )
            return self._fail(
                raw_goal,
                "normalization",
                "Empty goal",
                stages,
                recoverable=True,
            )

        self._current_continuation = None
        if self._continuity is not None:
            try:
                cr = self._continuity.detect(raw_goal)
                if cr.is_continuation:
                    self._current_continuation = cr.to_dict()
            except Exception:
                pass

        goal_id: str | None = None
        if self._goals is not None:
            try:
                created = self._goals.create_goal(description=raw_goal)
                goal_id = created.goal_id
                self._record_decision(
                    goal_id=goal_id,
                    decision_type="goal_created",
                    description=f"Goal entered pipeline: {raw_goal[:80]}",
                    alternatives=[],
                    rationale=None,
                )
            except Exception:
                pass

        # ---- Phase 11: Human normalization ----
        active_descs: List[str] = []
        if self._goals is not None:
            active_descs = [
                g.description for g in self._goals.list_goals()
                if g.lifecycle_state == "active"
            ]
        normalizer_result = self._normalizer.normalize(raw_goal, active_goal_descriptions=active_descs)
        normalized = normalizer_result.normalized
        if normalizer_result.transformations:
            warnings.append(f"Normalized: {'; '.join(normalizer_result.transformations)}")

        # Continuation requests skip clarification — the original goal was already vetted
        if normalizer_result.is_continuation:
            stages.append(
                StageRecord(
                    stage="intent_clarification",
                    status="ok",
                    detail="skipped — continuation request",
                )
            )
            stages.append(
                StageRecord(
                    stage="human_normalization",
                    status="ok",
                    detail=f"continuation from '{raw_goal[:50]}'",
                )
            )
        else:
            stages.append(
                StageRecord(
                    stage="human_normalization",
                    status="ok",
                    detail=",".join(normalizer_result.transformations) if normalizer_result.transformations else "no changes",
                )
            )

        # ---- v1.9: Clarification gate ----
        if normalizer_result.is_continuation:
            stages.append(
                StageRecord(
                    stage="intent_clarification",
                    status="ok",
                    detail="skipped — continuation",
                )
            )
        else:
            clarification = self._clarifier.clarify(normalized)
            if clarification.status != IntentStatus.EXECUTABLE:
                stages.append(
                    StageRecord(
                        stage="intent_clarification",
                        status="failed" if clarification.status == IntentStatus.NON_EXECUTABLE else "ok",
                        detail=f"status={clarification.status.value}",
                    )
                )
                if clarification.status == IntentStatus.NON_EXECUTABLE:
                    if goal_id:
                        self._update_goal_state(goal_id, "blocked")
                        self._record_decision(
                            goal_id=goal_id,
                            decision_type="clarification_blocked",
                            description="Goal rejected as non-executable by clarification gate",
                            rationale=clarification.ambiguity_warnings[0] if clarification.ambiguity_warnings else None,
                        )
                    self._emit_feedback(
                        goal_id=goal_id,
                        action=raw_goal,
                        outcome="blocked",
                        deviation_type="mismatch",
                        severity="low",
                        reason_code="clarification_rejected",
                    )
                else:
                    self._emit_feedback(
                        goal_id=goal_id,
                        action=raw_goal,
                        outcome="partial",
                        deviation_type="partial_completion",
                        severity="low",
                        reason_code="clarification_needed",
                    )
                return PipelineResult(
                    goal=raw_goal,
                    status="clarification_required",
                    clarification=clarification,
                    stages=stages,
                    warnings=list(clarification.ambiguity_warnings),
                    continuation=self._current_continuation,
                )

            stages.append(
                StageRecord(
                    stage="intent_clarification",
                    status="ok",
                    detail=f"status={clarification.status.value}",
                )
            )

        if goal_id:
            self._record_decision(
                goal_id=goal_id,
                decision_type="clarification_resolved",
                description="Goal passed clarification gate as executable",
                alternatives=None,
                rationale=None,
            )

        plan_result = self._planner.plan(normalized, mode=mode)
        failed_plan_stage = plan_result.failure_stage

        if plan_result.status != "planned":
            stages.append(
                StageRecord(
                    stage=failed_plan_stage,
                    status="failed",
                    detail=plan_result.errors[0] if plan_result.errors else "Planning failed",
                )
            )
            if goal_id:
                self._update_goal_state(goal_id, "failed")
                self._record_decision(
                    goal_id=goal_id,
                    decision_type="planning_failed",
                    description=f"Planning failed at {failed_plan_stage}",
                    rationale=plan_result.errors[0] if plan_result.errors else None,
                )
            self._emit_feedback(
                goal_id=goal_id,
                action=raw_goal,
                outcome="failed",
                deviation_type="failure",
                severity="medium",
                reason_code="planning_failed",
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

        if goal_id:
            path = getattr(plan_result, "intent_type", "unknown")
            step_count = getattr(plan_result, "step_count", 0)
            self._record_decision(
                goal_id=goal_id,
                decision_type="planning_path_chosen",
                description=f"Planning path: {path}, {step_count} steps, mode={mode.value}",
                alternatives=["SimpleParser", "Decomposer"],
                rationale=f"Intent type: {path}, Mode: {mode.value}",
            )
            self._record_decision(
                goal_id=goal_id,
                decision_type="execution_mode_chosen",
                description=f"Execution mode: {mode.value}",
                alternatives=["normal", "stress_test", "failure_test"],
                rationale=f"ExecutionSpec: {spec.spec_id}",
            )

        warnings.extend(plan_result.errors)
        structured_steps: List[StructuredStep] = list(plan_result.structured_steps or [])
        dag = plan_result.dag
        pipeline_spec = plan_result.goal_spec

        pre_errors: List[str] = []
        pre_errors.extend(self._fidelity.validate(pipeline_spec, structured_steps, dag))
        structural = self._dag_validator.validate(dag, spec=spec)
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
            if goal_id:
                self._update_goal_state(goal_id, "blocked")
                self._record_decision(
                    goal_id=goal_id,
                    decision_type="goal_blocked",
                    description=f"Pre-execution validation failed: {pre_errors[0][:80]}",
                    rationale=pre_errors[0] if pre_errors else None,
                )
            self._emit_feedback(
                goal_id=goal_id,
                action=raw_goal,
                outcome="blocked",
                deviation_type="mismatch",
                severity="medium",
                reason_code="validation_failed",
            )
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

        execution = self._executor.execute(dag, normalized)
        stages.append(
            StageRecord(
                stage="execution",
                status="ok" if execution.status == "success" else "failed",
                detail=execution.status,
            )
        )
        stages.append(StageRecord(stage="trace_collection", status="ok", detail=""))

        if execution.status not in ("success",):
            if goal_id:
                self._update_goal_state(goal_id, "failed")
                self._record_decision(
                    goal_id=goal_id,
                    decision_type="goal_failed",
                    description=f"Execution failed with status: {execution.status}",
                    rationale=f"Steps executed: {execution.steps_executed}",
                )
            self._emit_feedback(
                goal_id=goal_id,
                action=raw_goal,
                outcome="failed",
                deviation_type="failure",
                severity="high",
                reason_code="execution_failed",
            )
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
            spec=pipeline_spec,
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
            if goal_id:
                self._update_goal_state(goal_id, "blocked")
                issue = evaluation.issues[0] if evaluation.issues else "Semantic check failed"
                self._record_decision(
                    goal_id=goal_id,
                    decision_type="goal_blocked",
                    description=f"Semantic evaluation failed: {issue[:80]}",
                    rationale=issue,
                )
            self._emit_feedback(
                goal_id=goal_id,
                action=raw_goal,
                outcome="failed",
                deviation_type="mismatch",
                severity="medium",
                reason_code="evaluation_failed",
            )
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

        if goal_id:
            self._update_goal_state(goal_id, "completed")
            self._record_decision(
                goal_id=goal_id,
                decision_type="goal_completed",
                description="Goal completed successfully",
                rationale=f"Steps executed: {execution.steps_executed}",
            )
        self._emit_feedback(
            goal_id=goal_id,
            action=raw_goal,
            outcome="success",
            deviation_type="none",
            severity="low",
            reason_code="success",
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
            continuation=self._current_continuation,
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
            continuation=getattr(self, "_current_continuation", None),
            execution=execution,
            evaluation=evaluation,
            pre_execution_passed=pre_passed,
            warnings=warnings or [],
        )


