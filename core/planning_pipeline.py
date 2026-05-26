# core/planning_pipeline.py
#
# v1.9.1: Intent → Normalization → Parsing → DAG construction (single responsibility per stage).
#
# INVARIANT: PlanningPipeline is the ONLY routing authority.
# Exactly one path executes per call: SimpleParser | Decomposer | error.
# No fallback, no mixed-path execution, no state across calls.

from __future__ import annotations

import logging
from typing import List

from core.dag_builder import DAGBuilder
from core.dag_node import CapabilityManifest
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

    def plan(self, goal: str) -> PlanResult:
        raw_goal = (goal or "").strip()
        intent = self._classifier.classify(raw_goal)
        intent_type = intent["type"]
        nl_steps = extract_nl_steps(raw_goal)
        spec = GoalSpec.from_goal(raw_goal, nl_steps, intent_type)

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

            # --- DAG construction (shared only for A and B) ---
            build_result = self._builder.build(steps)
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

            # v1.5: Attach CapabilityManifest after DAG construction.
            # Derives capabilities ONLY from tool contracts and explicit rule mapping.
            dag = self._attach_capability_manifest(dag)

            logger.info(
                "plan intent=%s path=%s node_count=%d status=planned",
                intent_type, path, len(dag.nodes),
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
                goal_spec=spec,
            )

        except Exception as exc:
            return plan_failure(
                f"Planning pipeline error: {exc}",
                raw_goal=raw_goal,
                intent_type=intent_type,
                stage="parsing",
            )

    @staticmethod
    def _is_error_dag(dag) -> bool:
        return bool(
            len(dag.nodes) == 1
            and dag.nodes[0].tool_name == PLANNING_ERROR_TOOL
        )

    @staticmethod
    def _attach_capability_manifest(dag: Any) -> Any:
        """
        Attach a CapabilityManifest to the DAG after construction.

        Derives capabilities deterministically from tool names in the DAG.
        This is the ONLY place where manifests are created — no runtime inference.

        Returns a new DAG object with the manifest attached (immutable pattern).
        """
        tool_names = {n.tool_name for n in dag.nodes}

        # Derive capability IDs from tool contracts
        from core.capability import build_default_manifest

        manifest = build_default_manifest(
            dag_id=str(id(dag)),
            tool_names=tool_names,
        )

        # Convert to dict-based manifest (compatible with frozen DAG dataclass)
        manifest_dicts = []
        for cap in manifest.capabilities:
            cap_dict = {
                "capability_id": str(cap.capability_id),
                "display_name": cap.display_name,
                "description": cap.description,
                "allowed_tools": cap.allowed_tools,
                "scope": {
                    "allowed_path_prefixes": cap.scope.allowed_path_prefixes,
                    "allowed_paths": cap.scope.allowed_paths,
                    "max_bytes": cap.scope.max_bytes,
                    "max_steps": cap.scope.max_steps,
                    "max_outputs": cap.scope.max_outputs,
                },
                "constraints": dict(cap.constraints),
            }
            manifest_dicts.append(cap_dict)

        from dataclasses import replace

        cm = CapabilityManifest(
            dag_id=str(id(dag)),
            capabilities=manifest_dicts,
            strict_mode=True,
        )

        return replace(dag, capability_manifest=cm)
