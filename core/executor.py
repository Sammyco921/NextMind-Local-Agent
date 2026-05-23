from typing import Dict, Any, List


# =====================================================
# EXECUTION RESULT MODEL
# =====================================================

class ExecutionResult:
    def __init__(self, goal: str):
        self.goal = goal
        self.status = "success"
        self.trace: List[Dict[str, Any]] = []
        self.steps_executed = 0

    def add_step(self, step_record: Dict[str, Any]):
        self.trace.append(step_record)

        if step_record["status"] != "success":
            self.status = "partial_failure"

        self.steps_executed += 1

    def to_dict(self):
        return {
            "goal": self.goal,
            "status": self.status,
            "steps_executed": self.steps_executed,
            "trace": self.trace,
        }


# =====================================================
# EXECUTOR (v1.1 STRICT ENGINE)
# =====================================================

class Executor:
    """
    Deterministic DAG executor.

    v1.1 guarantees:
    - no tool validation inside executor (registry owns it)
    - strict step execution order
    - structured trace output
    - no silent failures
    """

    def __init__(self, registry):
        self.registry = registry

    # -------------------------------------------------
    # MAIN ENTRYPOINT
    # -------------------------------------------------

    def execute(self, goal: str, steps: List[Dict[str, Any]]) -> ExecutionResult:

        result = ExecutionResult(goal)

        for step in steps:

            step_id = step.get("_id")
            tool_name = step["tool"]
            args = step.get("args", {})

            try:
                output = self.registry.run(tool_name, args)

                result.add_step({
                    "id": step_id,
                    "tool": tool_name,
                    "args": args,
                    "status": "success",
                    "result": output,
                    "note": None,
                })

            except Exception as e:

                result.add_step({
                    "id": step_id,
                    "tool": tool_name,
                    "args": args,
                    "status": "fail",
                    "result": {"error": str(e)},
                    "note": None,
                })

                # IMPORTANT v1.1 decision:
                # stop execution on first failure (deterministic behavior)
                break

        return result