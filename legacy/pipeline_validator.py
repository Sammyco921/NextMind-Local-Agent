# core/pipeline_validator.py
#
# NextMind v0.8 — Pipeline Validator (STRICT MODE)
#
# Role:
#   Enforce structural correctness of execution steps
#
# Guarantees:
#   - Every step has valid schema
#   - Invalid steps are rejected (not corrected silently)
#   - No tool inference or fallback logic
#
# Non-goals:
#   - No planning
#   - No tool selection
#   - No semantic repair


from typing import List, Dict, Any


class PipelineValidator:
    """
    Strict schema validator for execution steps.
    """

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def validate(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

        if not isinstance(steps, list):
            return []

        valid_steps = []

        for step in steps:
            if self._is_valid_step(step):
                valid_steps.append(step)

        return valid_steps

    # =====================================================
    # STEP VALIDATION
    # =====================================================

    def _is_valid_step(self, step: Dict[str, Any]) -> bool:

        if not isinstance(step, dict):
            return False

        # -------------------------
        # REQUIRED FIELDS
        # -------------------------
        tool = step.get("tool")
        args = step.get("args")

        if not isinstance(tool, str):
            return False

        if not isinstance(args, dict):
            return False

        # -------------------------
        # RESERVED FIELD CHECKS
        # -------------------------
        if "tool" not in step:
            return False

        if "args" not in step:
            return False

        # -------------------------
        # META STRUCTURE CHECK (optional but strict if present)
        # -------------------------
        meta = step.get("meta")
        if meta is not None and not isinstance(meta, dict):
            return False

        # -------------------------
        # DEPENDENCY CHECK (if present must be list)
        # -------------------------
        depends = step.get("depends_on", [])
        if not isinstance(depends, list):
            return False

        # -------------------------
        # FAIL-SAFE POLICY FIELDS
        # -------------------------
        if "on_fail" in step and not isinstance(step["on_fail"], str):
            return False

        return True