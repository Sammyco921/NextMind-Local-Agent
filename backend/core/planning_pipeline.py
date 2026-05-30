# core/planning_pipeline.py
#
# v1.9.1: Intent → Normalization → Parsing → DAG construction (single responsibility per stage).
#
# INVARIANT: PlanningPipeline is the ONLY routing authority.
# Exactly one path executes per call: SimpleParser | Decomposer | error.
# No fallback, no mixed-path execution, no state across calls.

from __future__ import annotations

import logging
from typing import Any, List, Optional

from core.dag_builder import DAGBuilder
from core.dag_node import DAG, DAGNode
from core.execution_mode import ExecutionMode, detect_mode_from_goal
from core.execution_spec import ExecutionSpec, FAILURE_INJECTION_TOOL
from core.goal_normalizer import GoalNormalizer
from core.goal_spec import GoalSpec, extract_nl_steps
from core.intent_classifier import IntentClassifier
from core.planning_errors import (
    PLANNING_ERROR_TOOL,
    empty_steps_failure,
    plan_failure,
)
from core.planning_types import PlanResult, StructuredStep
from core.simple_parser import SimpleParser
from core.decomposer import Decomposer


logger = logging.getLogger(__name__)


class PlanningPipeline:
    """
    Planning stages only — no execution, no semantic validation.
    Parser warnings do not fail planning; DAG build errors do.
    """

    def __init__(self, registry=None) -> None:
        self._classifier = IntentClassifier()
        self._normalizer = GoalNormalizer()
        self._simple_parser = SimpleParser()
        self._decomposer = Decomposer()
        self._builder = DAGBuilder()

    def plan(
        self,
        goal: str,
        mode: ExecutionMode | None = None,
    ) -> PlanResult:
        raw_goal = (goal or "").strip()

        if mode is None:
            mode = detect_mode_from_goal(raw_goal) or ExecutionMode.NORMAL

        spec = ExecutionSpec.for_mode(mode)

        intent = self._classifier.classify(raw_goal)
        intent_type = intent["type"]
        nl_steps = extract_nl_steps(raw_goal)
        spec_goal = GoalSpec.from_goal(raw_goal, nl_steps, intent_type)

        try:
            warnings: List[str] = []

            # --- Path A: SimpleParser (simple intents) ---
            if intent_type == "simple":
                normalized = self._normalizer.normalize(raw_goal)
                if not normalized.normalized_steps:
                    if normalized.warnings:
                        return plan_failure(
                            normalized.warnings[0],
                            raw_goal=raw_goal,
                            intent_type=intent_type,
                            stage="normalization",
                        )
                    return empty_steps_failure(raw_goal=raw_goal, stage="normalization")

                warnings.extend(normalized.warnings)
                steps, parse_warnings = self._simple_parser.parse_normalized(normalized)
                warnings.extend(parse_warnings)
                if not steps:
                    return plan_failure(
                        "SimpleParser produced no steps",
                        raw_goal=raw_goal,
                        intent_type=intent_type,
                        stage="parsing",
                    )

                path = "SimpleParser"

            # --- Path B: Decomposer (complex intents) ---
            elif intent_type == "complex":
                steps = self._decomposer.decompose(raw_goal)
                if not steps:
                    logger.info(
                        "plan intent=%s path=Decomposer node_count=0 status=empty_decompose",
                        intent_type,
                    )
                    return plan_failure(
                        "complex goal did not match any decomposition rule",
                        raw_goal=raw_goal,
                        intent_type=intent_type,
                        stage="parsing",
                    )

                path = "Decomposer"

            # --- Path C: error path (unknown intent types) ---
            else:
                logger.info(
                    "plan intent=%s path=None node_count=0 status=unknown_intent",
                    intent_type,
                )
                return plan_failure(
                    f"unknown intent type: {intent_type}",
                    raw_goal=raw_goal,
                    intent_type=intent_type,
                    stage="parsing",
                )

            # --- DAG construction (shared for A and B) ---
            build_result = self._builder.build(steps, spec=spec)
            warnings.extend(build_result.warnings)

            if not build_result.ok:
                logger.info(
                    "plan intent=%s path=%s node_count=0 status=dag_error errors=%s",
                    intent_type, path, build_result.errors[:3],
                )
                return plan_failure(
                    "DAG construction failed",
                    raw_goal=raw_goal,
                    errors=build_result.errors,
                    intent_type=intent_type,
                    stage="dag_construction",
                )

            dag = build_result.dag
            if self._is_error_dag(dag):
                logger.info(
                    "plan intent=%s path=%s node_count=0 status=error_dag",
                    intent_type, path,
                )
                return plan_failure(
                    str(dag.nodes[0].raw_args.get("message", "DAG build error")),
                    raw_goal=raw_goal,
                    intent_type=intent_type,
                    stage="dag_construction",
                )

            # ---- v1.7 ExecutionSpec: post-DAG transformations ----
            dag = self._apply_mode_transforms(dag, spec, warnings)

            # ---- v1.7 ExecutionSpec: validate failure node presence ----
            if spec.requires_failure_node:
                has_failure = any(
                    n.tool_name == FAILURE_INJECTION_TOOL for n in dag.nodes
                )
                if not has_failure:
                    return plan_failure(
                        f"ExecutionMode '{mode.value}' requires at least one "
                        f"failure-capable node but DAG has none",
                        raw_goal=raw_goal,
                        intent_type=intent_type,
                        stage="dag_construction",
                    )

            # v1.8: Attach ExecutionSpec identity to the DAG.
            dag = self._attach_spec_identity(dag, spec)


            logger.info(
                "plan intent=%s path=%s node_count=%d status=planned mode=%s",
                intent_type, path, len(dag.nodes), mode.value,
            )
            return PlanResult(
                dag=dag,
                status="planned",
                errors=warnings,
                intent_type=intent_type,
                step_count=len(dag.nodes),
                is_hypothesis=True,
                raw_goal=raw_goal,
                structured_steps=build_result.structured_steps,
                goal_spec=spec_goal,
            )

        except Exception as exc:
            return plan_failure(
                f"Planning pipeline error: {exc}",
                raw_goal=raw_goal,
                intent_type=intent_type,
                stage="parsing",
            )

    def _apply_mode_transforms(
        self,
        dag: Any,
        spec: ExecutionSpec,
        warnings: List[str],
    ) -> Any:
        """Apply post-DAG-build transformations defined by the ExecutionSpec."""
        if not spec.expand_dag and not spec.inject_failure:
            return dag

        from dataclasses import replace
        nodes = list(dag.nodes)

        # 1. Stress test expansion
        if spec.expand_dag:
            extra = spec.compute_synthetic_node_count(len(nodes))
            if extra > 0:
                noops = self._builder.compute_stress_noops(nodes, extra)
                nodes.extend(noops)
                warnings.append(
                    f"[mode={spec.mode.value}] Expanded DAG from {len(nodes) - extra} "
                    f"to {len(nodes)} nodes"
                )

        # 2. Failure node injection
        if spec.inject_failure or spec.requires_failure_node:
            base_count = len([n for n in nodes if not n.metadata.get("synthetic")])
            insert_at = ExecutionSpec.compute_failure_insertion_index(base_count)

            dep_ids: List[str] = []
            non_synthetic = [n for n in nodes if not n.metadata.get("synthetic")]
            insert_idx = min(insert_at, len(non_synthetic) - 1) if non_synthetic else 0
            if insert_idx > 0 and non_synthetic:
                dep_ids = [non_synthetic[insert_idx - 1].node_id]

            failure_node = self._builder.make_failure_node(
                node_id=f"n{len(nodes)}",
                dependencies=dep_ids,
                failure_type="capability_violation",
            )
            nodes.append(failure_node)
            warnings.append(
                f"[mode={spec.mode.value}] Injected failure node at position "
                f"{insert_at} with deps={dep_ids}"
            )

        return replace(dag, nodes=nodes)

    @staticmethod
    def _attach_spec_identity(dag: Any, spec: ExecutionSpec) -> Any:
        """Attach ExecutionSpec identity (spec_id, spec_hash) to the DAG."""
        from dataclasses import replace
        return replace(
            dag,
            spec_id=spec.spec_id,
            spec_hash=spec.spec_hash,
        )

    @staticmethod
    def _is_error_dag(dag) -> bool:
        return bool(
            len(dag.nodes) == 1
            and dag.nodes[0].tool_name == PLANNING_ERROR_TOOL
        )

    @staticmethod
    def _attach_spec_identity(dag: Any, spec: ExecutionSpec) -> Any:
        """Attach ExecutionSpec identity (spec_id, spec_hash) to the DAG."""
        from dataclasses import replace
        return replace(
            dag,
            spec_id=spec.spec_id,
            spec_hash=spec.spec_hash,
        )
