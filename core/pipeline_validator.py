# core/pipeline_validator.py
#
# NextMind v0.7 — Pipeline Validator
#
# Role:
#   This is the HARD BOUNDARY between planning and execution.
#
# It ensures:
#   - All steps are structurally valid
#   - Required fields exist
#   - No malformed tool calls reach scheduler/executor
#   - Steps are normalized into a strict schema
#
# This layer does NOT:
#   - Decide execution order
#   - Infer intent
#   - Execute anything
#   - Repair semantic logic


from __future__ import annotations

from typing import List, Dict, Any, Optional


# =========================================================
# VALIDATOR OUTPUT TYPE (conceptual contract)
# =========================================================
#
# Every validated step must match:
#
# {
#   "tool": str,
#   "args": dict,
#   "on_fail": str | None,
#   "fallback": dict | None,
#   "depends_on": list[str],
#   "meta": dict
# }


class PipelineValidator:
    """
    Strict structural validator for planner output.
    """

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def validate(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not isinstance(steps, list):
            raise ValueError("PipelineValidator: steps must be a list")

        if not steps:
            raise ValueError("PipelineValidator: empty step list")

        validated: List[Dict[str, Any]] = []

        for idx, step in enumerate(steps):
            v = self._validate_step(step, idx)
            if v is not None:
                validated.append(v)

        if not validated:
            raise ValueError("PipelineValidator: no valid steps after validation")

        return validated

    # =====================================================
    # SINGLE STEP VALIDATION
    # =====================================================

    def _validate_step(self, step: Dict[str, Any], idx: int) -> Optional[Dict[str, Any]]:
        if not isinstance(step, dict):
            return None

        tool = step.get("tool")
        args = step.get("args")

        # -------------------------------
        # HARD REQUIREMENTS
        # -------------------------------

        if not tool or not isinstance(tool, str):
            return None

        if args is None:
            args = {}

        if not isinstance(args, dict):
            return None

        # -------------------------------
        # SANITIZE OPTIONAL FIELDS
        # -------------------------------

        on_fail = step.get("on_fail")
        fallback = step.get("fallback")
        depends_on = step.get("depends_on")

        if depends_on is None:
            depends_on = []

        if not isinstance(depends_on, list):
            depends_on = []

        # fallback must be dict or None
        if fallback is not None and not isinstance(fallback, dict):
            fallback = None

        # -------------------------------
        # NORMALIZATION RULES
        # -------------------------------

        normalized = {
            "tool": tool,
            "args": args,
            "on_fail": self._normalize_on_fail(on_fail),
            "fallback": fallback,
            "depends_on": depends_on,
            "meta": {
                "validated": True,
                "index": idx,
            }
        }

        return normalized

    # =====================================================
    # on_fail NORMALIZATION
    # =====================================================

    def _normalize_on_fail(self, value: Any) -> str:
        """
        Ensures on_fail is always one of:
          - "abort"
          - "continue"
          - "fallback"
        """

        if value not in ("abort", "continue", "fallback"):
            # default safe behavior
            return "abort"

        return value

    # =====================================================
    # OPTIONAL: STRICT MODE CHECK
    # =====================================================

    def strict_check(self, step: Dict[str, Any]) -> bool:
        """
        Can be used by tests or debugging tools.
        """
        return (
            isinstance(step, dict)
            and isinstance(step.get("tool"), str)
            and isinstance(step.get("args"), dict)
        )