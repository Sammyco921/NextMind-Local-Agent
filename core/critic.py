"""
NextMind Critic (v0)

Design principle:
- NO LLM
- NO subjective evaluation
- ONLY structural + execution validation

The critic answers one question:
→ Did the tool call succeed or fail?
"""

from typing import Dict, Any


class Critic:

    def evaluate_step(
        self,
        step: Dict[str, Any],
        execution_result: Dict[str, Any]
    ) -> Dict[str, Any]:

        """
        Deterministic evaluation of tool execution.
        """

        step_id = step.get("id")

        status = execution_result.get("status")
        error = execution_result.get("error")

        # ----------------------------------------------------
        # Success cases (strict + fallback safe)
        # ----------------------------------------------------

        if status == "success" and error is None:
            return {
                "status": "pass",
                "step_id": step_id,
                "reason": None
            }

        # ----------------------------------------------------
        # Failure / ambiguous cases
        # ----------------------------------------------------

        return {
            "status": "fail",
            "step_id": step_id,
            "reason": error or "Execution did not succeed",
            "fix_suggestion": "Check tool arguments, tool implementation, and executor mapping."
        }
