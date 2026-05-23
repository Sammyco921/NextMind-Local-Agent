from typing import Dict, Any, List

from core.validator import Validator, ValidationResult
from tools.tool_registry import ToolRegistry


class Orchestrator:
    """
    v0.9 Deterministic Execution Orchestrator

    Responsibilities:
    - Request plans from planner
    - Validate execution steps
    - Execute tools deterministically
    - Track execution history
    - Return structured execution results

    Non-goals:
    - No planning logic
    - No validation logic
    - No tool schema ownership
    - No auto-repair
    - No hidden fallback behavior
    """

    def __init__(
        self,
        planner,
        registry: ToolRegistry,
        validator: Validator
    ):

        self.planner = planner
        self.registry = registry
        self.validator = validator

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def run(self, goal: str) -> Dict[str, Any]:

        # -------------------------------------------------
        # PLAN GENERATION
        # -------------------------------------------------

        plan = self.planner.plan(goal)

        if not plan:

            return {
                "goal": goal,
                "status": "fail",
                "phase": "planning",
                "steps_executed": 0,
                "history": [],
                "error": "No valid execution plan generated"
            }

        # -------------------------------------------------
        # PLAN VALIDATION
        # -------------------------------------------------

        validation = self.validator.validate_plan(plan)

        if not validation.allowed:

            return {
                "goal": goal,
                "status": "fail",
                "phase": "validation",
                "steps_executed": 0,
                "history": [],
                "validation_errors": validation.errors,
                "validation_warnings": validation.warnings
            }

        # -------------------------------------------------
        # EXECUTION
        # -------------------------------------------------

        history: List[Dict[str, Any]] = []

        steps_executed = 0

        execution_failed = False

        for index, step in enumerate(plan):

            tool_name = step["tool"]
            args = step["args"]

            # ---------------------------------------------
            # TOOL LOOKUP
            # ---------------------------------------------

            tool_fn = self.registry.get(tool_name)

            if tool_fn is None:

                history.append({
                    "step": step,
                    "result": {
                        "status": "fail",
                        "error": f"unknown tool '{tool_name}'"
                    }
                })

                execution_failed = True
                continue

            # ---------------------------------------------
            # EXECUTION
            # ---------------------------------------------

            try:

                output = tool_fn(**args)

                history.append({
                    "step": step,
                    "result": {
                        "status": "success",
                        "output": output
                    }
                })

                steps_executed += 1

            except Exception as e:

                history.append({
                    "step": step,
                    "result": {
                        "status": "fail",
                        "error": str(e)
                    }
                })

                execution_failed = True

                # -----------------------------------------
                # FAILURE POLICY
                # -----------------------------------------

                if step.get("on_fail") == "abort":
                    break

        # -------------------------------------------------
        # FINAL STATUS
        # -------------------------------------------------

        final_status = (
            "fail"
            if execution_failed
            else "success"
        )

        return {
            "goal": goal,
            "status": final_status,
            "phase": "execution",
            "steps_executed": steps_executed,
            "history": history
        }