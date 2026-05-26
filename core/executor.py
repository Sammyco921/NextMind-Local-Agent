# core/executor.py
#
# Step-list executor (legacy step format). Uses shared types and tool registry.

from __future__ import annotations

from typing import Any, Dict, List

from core.tool_registry import ToolRegistry
from core.types import ExecutionResult


class Executor:
    """Deterministic step-list executor for dict-based steps."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(self, goal: str, steps: List[Dict[str, Any]]) -> ExecutionResult:
        trace: List[Dict[str, Any]] = []
        status = "success"

        for step in steps:
            step_id = step.get("_id")
            tool_name = step["tool"]
            args = step.get("args", {})

            try:
                output = self.registry.run(tool_name, args)
                trace.append({
                    "id": step_id,
                    "tool": tool_name,
                    "args": args,
                    "status": "success",
                    "result": output,
                    "note": None,
                })
            except Exception as e:
                status = "partial_failure"
                trace.append({
                    "id": step_id,
                    "tool": tool_name,
                    "args": args,
                    "status": "fail",
                    "result": {"error": str(e)},
                    "note": None,
                })
                break

        return ExecutionResult(
            goal=goal,
            status=status,
            trace=trace,
            steps_executed=len(trace),
        )
