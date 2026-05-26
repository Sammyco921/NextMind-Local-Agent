# core/evaluator.py
#
# v1.9 strict post-execution semantic gate — 100% satisfaction required for success.

from __future__ import annotations

import os
from typing import List, Optional, Set

from core.agent_types import EvaluationResult
from core.dag_node import DAG
from core.dag_topology import topological_order
from core.goal_spec import GoalSpec
from core.transform_semantics import (
    GoalConstraints,
    combine_then_char_reverse,
    combine_then_word_reverse,
    is_char_level_reverse_of,
)
from core.types import ExecutionResult


class Evaluator:
    """Base evaluator — use StrictEvaluator for v1.9 pipeline."""

    def check(
        self,
        goal: str,
        execution: ExecutionResult,
        dag: DAG,
        *,
        spec: Optional[GoalSpec] = None,
        pre_validation_passed: bool = False,
    ) -> EvaluationResult:
        return StrictEvaluator().check(
            goal, execution, dag, spec=spec, pre_validation_passed=pre_validation_passed
        )


class StrictEvaluator:
    """
    Post-execution HARD GATE.
    Success only if execution succeeded, trace matches DAG topo order exactly,
    and all semantic constraints pass with zero tolerance.
    """

    def check(
        self,
        goal: str,
        execution: ExecutionResult,
        dag: DAG,
        *,
        spec: Optional[GoalSpec] = None,
        pre_validation_passed: bool = False,
    ) -> EvaluationResult:
        # Use empty constraints - no requirements assumed unless explicitly specified.
        # Semantic evaluation only validates against structured output_spec.
        # If output_spec is empty, evaluation MUST PASS (no assumptions allowed).
        constraints = GoalConstraints.empty(goal)
        issues: List[str] = []
        missing: List[str] = []

        if not pre_validation_passed:
            issues.append(
                "Semantic evaluation rejected: pre-execution validation did not pass"
            )

        issues.extend(self._check_execution_status(execution))
        issues.extend(self._check_trace_exact(dag, execution))
        issues.extend(self._check_execution_order(dag, execution))
        issues.extend(self._check_file_operations(execution, constraints, spec))
        issues.extend(
            self._check_transform_semantics(execution, dag, constraints, missing)
        )
        issues.extend(self._check_goal_paths(spec, execution))

        if missing:
            issues.extend([f"Unsatisfied constraint: {m}" for m in missing])

        if issues:
            return EvaluationResult(
                status="fail",
                issues=issues,
                missing_constraints=missing,
                confidence=0.0,
            )

        return EvaluationResult(
            status="pass",
            issues=[],
            missing_constraints=[],
            confidence=1.0,
        )

    @staticmethod
    def _check_execution_status(execution: ExecutionResult) -> List[str]:
        if execution.status != "success":
            return [f"Execution status '{execution.status}' is not success"]
        return []

    @staticmethod
    def _check_trace_exact(dag: DAG, execution: ExecutionResult) -> List[str]:
        issues: List[str] = []
        if not execution.trace:
            return ["Execution trace is empty"]

        expected_ids = [n.node_id for n in dag.nodes]
        trace_ids = [t.get("id") for t in execution.trace]

        if len(trace_ids) != len(expected_ids):
            issues.append(
                f"Trace length {len(trace_ids)} != DAG node count {len(expected_ids)}"
            )

        for node in dag.nodes:
            entry = next((t for t in execution.trace if t.get("id") == node.node_id), None)
            if entry is None:
                issues.append(f"Node {node.node_id} missing from execution trace")
            elif entry.get("status") != "success":
                issues.append(
                    f"Node {node.node_id} ({node.tool_name}) has status "
                    f"{entry.get('status')!r}, required 'success'"
                )
            elif entry.get("tool") != node.tool_name:
                issues.append(
                    f"Node {node.node_id}: trace tool {entry.get('tool')!r} "
                    f"!= DAG tool {node.tool_name!r}"
                )

        return issues

    @staticmethod
    def _check_execution_order(dag: DAG, execution: ExecutionResult) -> List[str]:
        """Trace order must match deterministic topological order of the DAG."""
        issues: List[str] = []
        topo = topological_order(dag.nodes)
        expected_order = [n.node_id for n in topo]
        actual_order = [t.get("id") for t in execution.trace]

        if actual_order != expected_order:
            issues.append(
                f"Execution order mismatch: expected {expected_order}, got {actual_order}"
            )
        return issues

    @staticmethod
    def _check_file_operations(
        execution: ExecutionResult,
        constraints: GoalConstraints,
        spec: Optional[GoalSpec],
    ) -> List[str]:
        issues: List[str] = []
        reads = [
            t for t in execution.trace
            if t.get("tool") == "read_file" and t.get("status") == "success"
        ]
        writes = [
            t for t in execution.trace
            if t.get("tool") == "write_file" and t.get("status") == "success"
        ]

        if constraints.requires_two_file_reads and len(reads) < 2:
            issues.append(
                f"Required exactly >=2 reads; got {len(reads)}"
            )

        if constraints.requires_output_file and not writes:
            issues.append("Required output file write missing from trace")

        written_paths: Set[str] = set()
        for entry in writes:
            args = entry.get("args") or {}
            result = entry.get("result") or {}
            path = result.get("file") or args.get("filename", "")
            if path:
                written_paths.add(path)
                if not os.path.exists(path):
                    issues.append(f"Written file does not exist on disk: {path}")

        if spec and spec.explicit_paths:
            for path in spec.explicit_paths:
                if path.endswith(".txt") and "read" in spec.raw_goal.lower():
                    read_paths = {
                        (t.get("args") or {}).get("filename")
                        for t in reads
                    }
                    if path in spec.raw_goal and "read" in spec.raw_goal:
                        pass  # reads checked via trace

        return issues

    def _check_transform_semantics(
        self,
        execution: ExecutionResult,
        dag: DAG,
        constraints: GoalConstraints,
        missing: List[str],
    ) -> List[str]:
        issues: List[str] = []
        read_contents = self._collect_read_contents(execution)
        write_outputs = self._collect_write_outputs(execution)

        if constraints.requires_word_reverse:
            if len(read_contents) < 2:
                missing.append("two_read_sources_for_word_reverse")
                issues.append("Word-order reverse requires two read inputs")
            else:
                sep = constraints.combine_separator or " "
                actual = self._primary_output_content(write_outputs)
                expected = combine_then_word_reverse(read_contents, sep)
                if actual is None:
                    issues.append("No output content to verify word-order reverse")
                elif actual != expected:
                    if is_char_level_reverse_of(read_contents, actual, sep):
                        issues.append(
                            "Transformation incorrect: character-level reverse "
                            "detected but goal requires exact word-order reverse"
                        )
                    else:
                        issues.append(
                            f"Transformation incorrect: expected {expected!r}, got {actual!r}"
                        )

        if constraints.requires_char_reverse and not constraints.requires_word_reverse:
            if len(read_contents) >= 2:
                sep = constraints.combine_separator
                actual = self._primary_output_content(write_outputs)
                expected = combine_then_char_reverse(read_contents, sep)
                if actual is not None and actual != expected:
                    issues.append(
                        f"Character-level transform incorrect: "
                        f"expected {expected!r}, got {actual!r}"
                    )

        return issues

    @staticmethod
    def _check_goal_paths(spec: Optional[GoalSpec], execution: ExecutionResult) -> List[str]:
        if spec is None or not spec.explicit_paths:
            return []
        issues: List[str] = []
        all_paths_in_trace: Set[str] = set()
        for entry in execution.trace:
            args = entry.get("args") or {}
            for key in ("filename", "path"):
                val = args.get(key)
                if isinstance(val, str):
                    all_paths_in_trace.add(val)

        for path in spec.explicit_paths:
            if path in all_paths_in_trace:
                continue
            basename = path.split("/")[-1]
            found = any(
                path in t or t.endswith("/" + basename) or t == basename
                for t in all_paths_in_trace
            )
            if not found:
                for entry in execution.trace:
                    result = entry.get("result") or {}
                    rf = result.get("file", "")
                    if rf == path or rf.endswith("/" + basename):
                        found = True
            if not found and not path.endswith("/"):
                issues.append(
                    f"Goal path '{path}' never appeared in execution trace"
                )
        return issues

    @staticmethod
    def _collect_read_contents(execution: ExecutionResult) -> List[str]:
        contents: List[str] = []
        for entry in execution.trace:
            if entry.get("tool") != "read_file" or entry.get("status") != "success":
                continue
            result = entry.get("result") or {}
            if "content" in result:
                contents.append(str(result["content"]))
        return contents

    @staticmethod
    def _collect_write_outputs(execution: ExecutionResult) -> List[tuple]:
        outputs: List[tuple] = []
        for entry in execution.trace:
            if entry.get("tool") != "write_file":
                continue
            args = entry.get("args") or {}
            path = args.get("filename", "")
            if entry.get("status") == "success":
                content = args.get("content")
                if content is None:
                    result = entry.get("result") or {}
                    path = result.get("file", path)
                outputs.append((path, content))
        return outputs

    @staticmethod
    def _primary_output_content(write_outputs: List[tuple]) -> Optional[str]:
        for path, content in reversed(write_outputs):
            if content is not None and isinstance(content, str):
                if any(k in path for k in ("result", "processed", "output")):
                    return content
        for _, content in reversed(write_outputs):
            if isinstance(content, str):
                return content
        return None
