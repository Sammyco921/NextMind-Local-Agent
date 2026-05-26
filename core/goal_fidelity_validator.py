# core/goal_fidelity_validator.py
#
# v1.9.1: pre-execution goal↔DAG alignment (validation layer only).

from __future__ import annotations

import re
from typing import Dict, List, Set

from core.dag_node import DAG
from core.goal_spec import GoalSpec
from core.planning_types import StructuredStep


class GoalFidelityValidator:
    """Verify DAG aligns with goal — does not parse or normalize."""

    def validate(
        self,
        spec: GoalSpec,
        steps: List[StructuredStep],
        dag: DAG,
    ) -> List[str]:
        """
        Pre-execution fidelity validation.
        
        Only validates structural alignment between structured steps and DAG.
        Does NOT validate goal paths against DAG nodes - that is a semantic
        check that belongs in post-execution evaluation, not pre-execution.
        
        File paths in the goal are entity values in ActionSpecs, not validation keys.
        """
        errors: List[str] = []

        if not steps:
            errors.append("No structured steps for fidelity check")
            return errors

        if len(dag.nodes) != len(steps):
            errors.append(
                f"DAG node count ({len(dag.nodes)}) != structured steps ({len(steps)})"
            )

        # Only structural checks - no goal path validation
        errors.extend(self._check_step_ordering(steps, dag))
        errors.extend(self._check_quoted_content_preserved(spec, steps))

        return errors

    @staticmethod
    def _literal_paths_in_dag(dag: DAG) -> Set[str]:
        paths: Set[str] = set()
        for node in dag.nodes:
            args = node.raw_args or {}
            for key in ("filename", "path"):
                val = args.get(key)
                if isinstance(val, str) and not val.startswith("$"):
                    paths.add(val)
        return paths

    def _check_explicit_paths(self, spec: GoalSpec, dag: DAG) -> List[str]:
        errors: List[str] = []
        dag_paths = self._literal_paths_in_dag(dag)

        for path in spec.explicit_paths:
            if path in dag_paths:
                continue
            basename = path.split("/")[-1]
            if any(p.endswith(basename) or basename in p for p in dag_paths):
                continue
            if path.endswith(".keep"):
                continue
            errors.append(
                f"Goal path '{path}' not found in DAG (exact or basename match required)"
            )
        return errors

    @staticmethod
    def _check_step_ordering(steps: List[StructuredStep], dag: DAG) -> List[str]:
        errors: List[str] = []
        for i, (step, node) in enumerate(zip(steps, dag.nodes)):
            expected_index = step.get("goal_step_index", i)
            node_index = node.metadata.get("goal_step_index", i)
            if expected_index != node_index:
                errors.append(
                    f"Ordering violation at step {i}: index {expected_index} vs {node_index}"
                )
        return errors

    @staticmethod
    def _check_quoted_content_preserved(
        spec: GoalSpec, steps: List[StructuredStep]
    ) -> List[str]:
        errors: List[str] = []
        for i, nl in enumerate(spec.nl_steps):
            if i >= len(steps):
                break
            if '"' not in nl:
                continue
            quoted = re.search(r'"([^"]*)"', nl)
            if not quoted:
                continue
            expected = quoted.group(1)
            content = (steps[i].get("args") or {}).get("content")
            if isinstance(content, str) and content != expected:
                errors.append(
                    f"Step {i + 1}: quoted content altered "
                    f"(expected {expected!r}, got {content!r})"
                )
        return errors
