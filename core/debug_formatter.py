# core/debug_formatter.py

from __future__ import annotations

from typing import Any, Dict, List, Union

from core.execution_context import ExecutionContext
from core.types import ExecutionResult


def format_execution_result(
    result: Union[ExecutionResult, ExecutionContext, Dict[str, Any]],
    *,
    goal: str = "",
    validation: Dict[str, Any] | None = None,
) -> str:
    """
    Format execution output into a readable structured log.
    Accepts ExecutionResult, ExecutionContext, or a plain result dict.
    """
    lines: List[str] = []
    lines.append("\n================ NEXTMIND EXECUTION REPORT ================\n")

    if goal:
        lines.append("GOAL:")
        lines.append(f"  {goal}\n")

    if validation is not None:
        lines.append("VALIDATION:")
        lines.append(f"  status: {validation.get('status')}")
        errors = validation.get("errors", [])
        if errors:
            lines.append("  errors:")
            for err in errors:
                lines.append(f"    - {err}")
        else:
            lines.append("  errors: none")
        lines.append("")

    if isinstance(result, ExecutionContext):
        status = "partial_failure" if result.errors else "success"
        trace = result.trace
        steps_executed = len(trace)
    elif isinstance(result, ExecutionResult):
        status = result.status
        trace = result.trace
        steps_executed = result.steps_executed
    elif isinstance(result, dict):
        status = result.get("status", "unknown")
        trace = result.get("trace", result.get("history", []))
        steps_executed = result.get("steps_executed", len(trace))
    else:
        status = getattr(result, "status", "unknown")
        trace = getattr(result, "trace", [])
        steps_executed = len(trace)

    lines.append("EXECUTION RESULT:")
    lines.append(f"  status: {status}")
    lines.append(f"  steps_executed: {steps_executed}")
    lines.append("")
    lines.append("STEP TRACE:")

    if not trace:
        lines.append("  (empty)")
    else:
        for i, entry in enumerate(trace):
            tool = entry.get("tool") or entry.get("tool_name", "?")
            node_id = entry.get("id") or entry.get("node_id", "?")
            step_status = entry.get("status", "?")
            res = entry.get("result", {})
            lines.append(f"  [{i}] {tool} ({node_id}) -> {step_status}")
            if isinstance(res, dict) and "error" in res:
                lines.append(f"      error: {res['error']}")
            elif isinstance(res, dict) and "content" in res:
                preview = str(res["content"])[:120]
                lines.append(f"      content: {preview}")

    lines.append("\n========================================================\n")
    return "\n".join(lines)


class DebugFormatter:
    """Backward-compatible wrapper around format_execution_result."""

    def format(
        self,
        goal: str,
        validation: Dict[str, Any],
        result: Any,
    ) -> str:
        return format_execution_result(
            result,
            goal=goal,
            validation=validation,
        )
