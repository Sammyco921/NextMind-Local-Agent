# core/executor.py
#
# NextMind v0.7 — Deterministic Executor
#
# Role:
#   Execute a fully validated and scheduled list of steps.
#
# Non-goals:
#   - No planning
#   - No validation
#   - No scheduling
#   - No reordering
#
# This is a pure interpreter over a linear schedule.


from __future__ import annotations

from typing import List, Dict, Any


# =====================================================
# EXECUTION RESULT
# =====================================================

class ExecutionResult:
    def __init__(self, goal: str, status: str, trace: List[Dict]):
        self.goal = goal
        self.status = status
        self.trace = trace

    def to_dict(self) -> Dict:
        return {
            "goal": self.goal,
            "status": self.status,
            "steps_executed": len(self.trace),
            "history": self.trace,
        }


# =====================================================
# EXECUTOR
# =====================================================

class Executor:
    """
    Deterministic step interpreter.

    Assumes:
      - Steps are already topologically ordered
      - Dependencies are already resolved
      - Input is structurally valid
    """

    def __init__(self, registry):
        self.registry = registry

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def execute(self, goal: str, steps: List[Dict[str, Any]]) -> ExecutionResult:
        trace: List[Dict] = []
        aborted = False

        # track step status for dependency logic
        status_map = {}

        for step in steps:
            step_id = step.get("_id")

            # -----------------------------
            # SKIP IF GLOBAL ABORT
            # -----------------------------
            if aborted:
                entry = self._trace(step, "skipped", None, "aborted")
                trace.append(entry)
                status_map[step_id] = "skipped"
                continue

            # -----------------------------
            # DEPENDENCY CHECK
            # -----------------------------
            deps = step.get("depends_on", [])
            if any(status_map.get(d) != "success" for d in deps):
                entry = self._trace(step, "skipped", None, "dependency_failed")
                trace.append(entry)
                status_map[step_id] = "skipped"
                continue

            # -----------------------------
            # EXECUTE STEP
            # -----------------------------
            tool_name = step["tool"]
            args      = step["args"]

            if not self.registry.has(tool_name):
                result = {"status": "fail", "error": f"Unknown tool '{tool_name}'"}
                entry = self._trace(step, "fail", result)
                trace.append(entry)
                status_map[step_id] = "fail"
                aborted = True
                continue

            tool = self.registry.get(tool_name)

            try:
                output = tool(**args)
                result = {"status": "success", "output": output}

                entry = self._trace(step, "success", result)
                trace.append(entry)
                status_map[step_id] = "success"
                continue

            except FileNotFoundError as e:
                result = {"status": "fail", "error": str(e)}

                # soft-fail path
                if step.get("on_fail") == "continue":
                    entry = self._trace(step, "soft_fail", result)
                    trace.append(entry)
                    status_map[step_id] = "soft_fail"
                    continue

                # fallback path
                if step.get("on_fail") == "fallback" and step.get("fallback"):
                    fb = step["fallback"]

                    try:
                        fb_tool = self.registry.get(fb["tool"])
                        fb_out = fb_tool(**fb.get("args", {}))

                        entry = self._trace(step, "soft_fail", result)
                        trace.append(entry)

                        fb_entry = self._trace(
                            {
                                "_id": f"{step_id}_fallback",
                                "tool": fb["tool"],
                                "args": fb.get("args", {}),
                            },
                            "success",
                            {"status": "success", "output": fb_out},
                        )
                        trace.append(fb_entry)

                        status_map[step_id] = "soft_fail"
                        continue

                    except Exception as fe:
                        entry = self._trace(step, "fail", {"error": str(fe)})
                        trace.append(entry)
                        status_map[step_id] = "fail"
                        aborted = True
                        continue

                # default hard fail
                entry = self._trace(step, "fail", result)
                trace.append(entry)
                status_map[step_id] = "fail"
                aborted = True
                continue

            except Exception as e:
                result = {"status": "fail", "error": str(e)}
                entry = self._trace(step, "fail", result)
                trace.append(entry)
                status_map[step_id] = "fail"
                aborted = True
                continue

        return ExecutionResult(
            goal=goal,
            status=self._compute_status(trace),
            trace=trace,
        )

    # =====================================================
    # TRACE FORMAT
    # =====================================================

    def _trace(self, step: Dict[str, Any], status: str, result: Any, note: str = None) -> Dict:
        return {
            "step": {
                "_id": step.get("_id"),
                "tool": step.get("tool"),
                "args": step.get("args"),
                "status": status,
            },
            "result": result,
            "note": note,
        }

    # =====================================================
    # FINAL STATUS
    # =====================================================

    def _compute_status(self, trace: List[Dict]) -> str:
        statuses = [t["step"]["status"] for t in trace]

        if any(s == "fail" for s in statuses):
            return "partial_failure"

        if any(s in ("soft_fail", "skipped") for s in statuses):
            return "success_with_warnings"

        return "success"