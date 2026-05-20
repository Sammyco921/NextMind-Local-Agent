# core/orchestrator.py
#
# NextMind v0.8 — Orchestrator (STRICT EXECUTION MODE)
#
# Key fixes:
#   - Reject empty plans immediately
#   - No silent execution of empty step sets
#   - Stronger failure phase labeling
#   - Consistent registry API usage (has/get/get_metadata)
#
# Role:
#   Deterministic execution controller only


from typing import Dict, Any, List

from core.pipeline_validator import PipelineValidator


class Orchestrator:

    def __init__(self, planner, registry, constraints_engine=None):
        self.planner = planner
        self.registry = registry
        self.validator = PipelineValidator()
        self.constraints = constraints_engine

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def run(self, goal: str) -> Dict[str, Any]:

        try:
            steps = self.planner.plan(goal)

            # 🔴 HARD GUARD: empty or invalid plan = immediate fail
            if not steps:
                return {
                    "goal": goal,
                    "status": "fail",
                    "steps_executed": 0,
                    "history": [],
                    "phase": "planning",
                    "error": "No valid execution plan generated"
                }

            steps = self.validator.validate(steps)

        except Exception as e:
            return {
                "goal": goal,
                "status": "fail",
                "steps_executed": 0,
                "history": [],
                "phase": "planning_or_validation",
                "error": str(e)
            }

        history = []
        executed = 0

        # =================================================
        # EXECUTION LOOP
        # =================================================

        for step in steps:

            tool_name = step["tool"]
            args = step["args"]

            # -------------------------
            # TOOL CHECK
            # -------------------------
            if not self.registry.has(tool_name):
                history.append(self._fail(step, f"Tool not found: {tool_name}"))
                continue

            tool = self.registry.get(tool_name)

            if tool is None:
                history.append(self._fail(step, f"Tool resolved to None: {tool_name}"))
                continue

            # -------------------------
            # CONSTRAINTS (optional)
            # -------------------------
            if self.constraints:
                result = self.constraints.evaluate(step)
                if not result.allowed:
                    history.append(self._fail(step, result.reason))
                    continue

            # -------------------------
            # EXECUTION
            # -------------------------
            try:
                output = tool(**args)

                history.append({
                    "step": step,
                    "result": {
                        "status": "success",
                        "output": output
                    },
                    "note": None
                })

                executed += 1

            except Exception as e:
                history.append(self._fail(step, str(e)))

        # =================================================
        # FINAL STATUS
        # =================================================

        status = "success" if executed == len(steps) else "success_with_warnings"

        return {
            "goal": goal,
            "status": status,
            "steps_executed": executed,
            "history": history,
            "phase": "execution"
        }

    # =====================================================
    # INTERNAL HELPERS
    # =====================================================

    def _fail(self, step: Dict[str, Any], error: str) -> Dict[str, Any]:
        return {
            "step": step,
            "result": {
                "status": "fail",
                "error": error
            },
            "note": None
        }