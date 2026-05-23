# core/debug_formatter.py

from typing import Any, Dict


# =====================================================
# DEBUG FORMATTER (v1.1)
# =====================================================

class DebugFormatter:
    """
    Converts execution state into human-readable diagnostics.
    """

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def format(self, goal: str, validation: Dict[str, Any], result: Any) -> str:

        lines = []

        lines.append("\n================ NEXTMIND DEBUG REPORT ================\n")

        # ---------------------------------------------
        # GOAL
        # ---------------------------------------------

        lines.append("GOAL:")
        lines.append(f"  {goal}\n")

        # ---------------------------------------------
        # VALIDATION PHASE
        # ---------------------------------------------

        lines.append("VALIDATION:")
        lines.append(f"  status: {validation.get('status')}")

        errors = validation.get("errors", [])
        if errors:
            lines.append("  errors:")
            for e in errors:
                lines.append(f"    - {e}")
        else:
            lines.append("  errors: none")

        lines.append("")

        # ---------------------------------------------
        # EXECUTION SUMMARY
        # ---------------------------------------------

        lines.append("EXECUTION RESULT:")
        lines.append(f"  status: {getattr(result, 'status', 'unknown')}")

        if hasattr(result, "trace"):
            lines.append(f"  steps_executed: {len(result.trace)}")

        lines.append("")

        # ---------------------------------------------
        # STEP TRACE
        # ---------------------------------------------

        lines.append("STEP TRACE:")

        trace = getattr(result, "trace", [])

        if not trace:
            lines.append("  (empty)")
        else:
            for i, t in enumerate(trace):
                step = t.get("step", {})
                res = t.get("result", {})
                status = step.get("status")

                lines.append(f"  [{i}] {step.get('tool')} -> {status}")

                if "error" in res:
                    lines.append(f"      error: {res['error']}")

                if "output" in res:
                    lines.append(f"      output: {str(res['output'])[:120]}")

        lines.append("\n========================================================\n")

        return "\n".join(lines)