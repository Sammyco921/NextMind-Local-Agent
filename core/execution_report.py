# core/execution_report.py

from __future__ import annotations

from typing import List, Dict, Any, Optional


# =====================================================
# STEP REPORT (atomic unit of execution output)
# =====================================================

class StepReport:
    """
    Structured representation of a single execution step result.
    """

    def __init__(
        self,
        step_id: str,
        tool: str,
        args: Dict[str, Any],
        status: str,
        result: Optional[Dict[str, Any]] = None,
        note: Optional[str] = None,
    ):
        self.step_id = step_id
        self.tool = tool
        self.args = args
        self.status = status
        self.result = result
        self.note = note

    # -------------------------------------------------
    # FACTORY HELPERS (used by executor)
    # -------------------------------------------------

    @staticmethod
    def success(step: Dict[str, Any], output: Any) -> "StepReport":
        return StepReport(
            step_id=step["_id"],
            tool=step["tool"],
            args=step.get("args", {}),
            status="success",
            result={"output": output},
        )

    @staticmethod
    def fail(step: Dict[str, Any], error: Dict[str, Any], note: str = None) -> "StepReport":
        return StepReport(
            step_id=step["_id"],
            tool=step["tool"],
            args=step.get("args", {}),
            status="fail",
            result=error,
            note=note,
        )

    @staticmethod
    def soft_fail(step: Dict[str, Any], error: Dict[str, Any], note: str = None) -> "StepReport":
        return StepReport(
            step_id=step["_id"],
            tool=step["tool"],
            args=step.get("args", {}),
            status="soft_fail",
            result=error,
            note=note,
        )

    @staticmethod
    def blocked(step: Dict[str, Any], error: Dict[str, Any], note: str = None) -> "StepReport":
        return StepReport(
            step_id=step["_id"],
            tool=step["tool"],
            args=step.get("args", {}),
            status="blocked",
            result=error,
            note=note,
        )

    @staticmethod
    def skip(step: Dict[str, Any], reason: str) -> "StepReport":
        return StepReport(
            step_id=step["_id"],
            tool=step["tool"],
            args=step.get("args", {}),
            status="skipped",
            result=None,
            note=reason,
        )

    # -------------------------------------------------
    # SERIALIZATION
    # -------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.step_id,
            "tool": self.tool,
            "args": self.args,
            "status": self.status,
            "result": self.result,
            "note": self.note,
        }


# =====================================================
# EXECUTION REPORT (full run aggregation)
# =====================================================

class ExecutionReport:
    """
    Final output object for a DAG execution run.
    """

    def __init__(
        self,
        goal: str,
        status: str,
        steps: List[StepReport],
    ):
        self.goal = goal
        self.status = status
        self.steps = steps

    # -------------------------------------------------
    # BUILD FROM TRACE
    # -------------------------------------------------

    @staticmethod
    def from_trace(goal: str, trace: List[StepReport]) -> "ExecutionReport":

        statuses = [s.status for s in trace]

        if "fail" in statuses:
            status = "partial_failure"
        elif "blocked" in statuses:
            status = "blocked"
        elif "soft_fail" in statuses or "skipped" in statuses:
            status = "success_with_warnings"
        else:
            status = "success"

        return ExecutionReport(
            goal=goal,
            status=status,
            steps=trace,
        )

    # -------------------------------------------------
    # CLEAN MACHINE OUTPUT
    # -------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "status": self.status,
            "steps_executed": len(self.steps),
            "trace": [s.to_dict() for s in self.steps],
        }

    # -------------------------------------------------
    # HUMAN READABLE SUMMARY (CLI)
    # -------------------------------------------------

    def pretty(self) -> str:
        lines = []
        lines.append("\n=== EXECUTION REPORT ===")
        lines.append(f"Goal: {self.goal}")
        lines.append(f"Status: {self.status}")
        lines.append(f"Steps: {len(self.steps)}\n")

        for s in self.steps:
            lines.append(
                f"[{s.status.upper()}] {s.tool} ({s.step_id})"
            )

            if s.note:
                lines.append(f"   note: {s.note}")

            if s.result:
                lines.append(f"   result: {s.result}")

        return "\n".join(lines)