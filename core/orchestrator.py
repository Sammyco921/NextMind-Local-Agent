"""
NextMind Orchestrator (v1 - strict control flow)

Design goals:
- NO logic duplication
- NO schema awareness (delegated downward)
- NO LLM calls here
- ONLY coordinates planner → executor → (optional critic)
"""

from typing import Dict, Any

from core.planner import Planner
from core.executor import Executor


class Orchestrator:
    """
    Central pipeline controller.
    """

    def __init__(self, planner: Planner, executor: Executor):
        self.planner = planner
        self.executor = executor

    # -------------------------------------------------
    # RUN FULL GOAL PIPELINE
    # -------------------------------------------------
    def run(self, goal: str) -> Dict[str, Any]:
        """
        End-to-end execution of a user goal.
        """

        # -------------------------------------------------
        # STEP 1: PLAN
        # -------------------------------------------------
        plan = self.planner.create_plan(goal)

        if not plan or "steps" not in plan:
            return {
                "status": "fail",
                "goal": goal,
                "error": plan.get("error", "Invalid plan"),
                "plan": plan
            }

        results = []

        # -------------------------------------------------
        # STEP 2: EXECUTE STEP BY STEP
        # -------------------------------------------------
        for step in plan["steps"]:

            execution_result = self.executor.execute_step(step)
            results.append(execution_result)

            print("\n[Planner Step]")
            print(step)

            print("\n[Execution Result]")
            print(execution_result)

            # -------------------------------------------------
            # STOP ON FAILURE (IMPORTANT FOR STABILITY)
            # -------------------------------------------------
            if execution_result["status"] == "fail":
                return {
                    "status": "fail",
                    "goal": goal,
                    "plan": plan,
                    "results": results,
                    "failed_step": step
                }

        # -------------------------------------------------
        # STEP 3: SUCCESS OUTPUT
        # -------------------------------------------------
        return {
            "status": "success",
            "goal": goal,
            "plan": plan,
            "results": results
        }
