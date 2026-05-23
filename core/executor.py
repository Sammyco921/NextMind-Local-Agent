# core/executor.py

from typing import List, Dict, Any

from core.contracts import (
    TOOL_STEP_SCHEMA,
    EXECUTOR_RESPONSE_SCHEMA,
    validate_contract,
)


# =====================================================
# EXECUTION RESULT
# =====================================================

class ExecutionResult:

    def __init__(
        self,
        goal: str,
        status: str,
        trace: List[Dict]
    ):
        self.goal = goal
        self.status = status
        self.trace = trace

    def to_dict(self) -> Dict:

        return {
            "goal": self.goal,
            "status": self.status,
            "steps_executed": len(self.trace),
            "trace": self.trace,
        }


# =====================================================
# EXECUTOR
# =====================================================

class Executor:
    """
    Deterministic DAG executor.

    Guarantees:
    - strict schema validation
    - deterministic execution order
    - dependency enforcement
    - registry-based execution
    - explicit failure handling
    """

    def __init__(self, registry):
        self.registry = registry

    # =================================================
    # MAIN EXECUTION
    # =================================================

    def execute(
        self,
        goal: str,
        steps: List[Dict[str, Any]]
    ) -> ExecutionResult:

        trace = []
        status_map = {}
        aborted = False

        for step in steps:

            # -----------------------------------------
            # GLOBAL ABORT
            # -----------------------------------------

            if aborted:

                trace.append({
                    "id": step["_id"],
                    "tool": step["tool"],
                    "args": step["args"],
                    "status": "skipped",
                    "result": None,
                    "note": "aborted"
                })

                continue

            # -----------------------------------------
            # STEP CONTRACT VALIDATION
            # -----------------------------------------

            try:

                normalized_step = {
                    "id": step["_id"],
                    "tool": step["tool"],
                    "args": step["args"]
                }

                validate_contract(
                    normalized_step,
                    TOOL_STEP_SCHEMA,
                    "ToolStep"
                )

            except Exception as e:

                trace.append({
                    "id": step["_id"],
                    "tool": step["tool"],
                    "args": step["args"],
                    "status": "fail",
                    "result": {
                        "error": str(e)
                    },
                    "note": None
                })

                aborted = True
                continue

            # -----------------------------------------
            # DEPENDENCY CHECK
            # -----------------------------------------

            deps = step.get("depends_on", [])

            dependency_failed = False

            for dep in deps:

                if status_map.get(dep) != "success":
                    dependency_failed = True
                    break

            if dependency_failed:

                trace.append({
                    "id": step["_id"],
                    "tool": step["tool"],
                    "args": step["args"],
                    "status": "skipped",
                    "result": None,
                    "note": "dependency_failed"
                })

                continue

            # -----------------------------------------
            # TOOL LOOKUP
            # -----------------------------------------

            tool_name = step["tool"]
            args = step["args"]

            if not self.registry.has(tool_name):

                trace.append({
                    "id": step["_id"],
                    "tool": tool_name,
                    "args": args,
                    "status": "fail",
                    "result": {
                        "error": f"Unknown tool: {tool_name}"
                    },
                    "note": None
                })

                aborted = True
                continue

            # -----------------------------------------
            # TOOL ARG VALIDATION
            # -----------------------------------------

            try:
                self.registry.validate_args(tool_name, args)

            except Exception as e:

                trace.append({
                    "id": step["_id"],
                    "tool": tool_name,
                    "args": args,
                    "status": "fail",
                    "result": {
                        "error": str(e)
                    },
                    "note": None
                })

                aborted = True
                continue

            # -----------------------------------------
            # EXECUTION
            # -----------------------------------------

            tool = self.registry.get(tool_name)

            try:

                output = tool(**args)

                response = {
                    "status": "success",
                    "output": output,
                    "error": None,
                    "step": step
                }

                validate_contract(
                    response,
                    EXECUTOR_RESPONSE_SCHEMA,
                    "ExecutorResponse"
                )

                trace.append({
                    "id": step["_id"],
                    "tool": tool_name,
                    "args": args,
                    "status": "success",
                    "result": output,
                    "note": None
                })

                status_map[step["_id"]] = "success"

            except Exception as e:

                response = {
                    "status": "fail",
                    "output": None,
                    "error": str(e),
                    "step": step
                }

                validate_contract(
                    response,
                    EXECUTOR_RESPONSE_SCHEMA,
                    "ExecutorResponse"
                )

                trace.append({
                    "id": step["_id"],
                    "tool": tool_name,
                    "args": args,
                    "status": "fail",
                    "result": {
                        "error": str(e)
                    },
                    "note": None
                })

                status_map[step["_id"]] = "fail"
                aborted = True

        # =================================================
        # FINAL STATUS
        # =================================================

        final_status = "success"

        for item in trace:

            if item["status"] == "fail":
                final_status = "partial_failure"
                break

        return ExecutionResult(
            goal=goal,
            status=final_status,
            trace=trace
        )