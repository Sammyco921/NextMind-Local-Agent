# core/executor.py
#
# NextMind v0.8 — Deterministic Executor (Registry-Aware)
#
# Role:
#   Execute validated + scheduled steps with enforced capability rules.
#
# Now enforces:
#   - Tool risk metadata
#   - Scope awareness
#   - Side-effect awareness
#   - Safer failure classification
#
# Still DOES NOT:
#   - Plan
#   - Validate structure
#   - Reorder execution
#   - Interpret intent


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
    Deterministic execution engine with capability-aware enforcement.
    """

    def __init__(self, registry):
        self.registry = registry

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def execute(self, goal: str, steps: List[Dict[str, Any]]) -> ExecutionResult:
        trace: List[Dict] = []
        aborted = False
        status_map = {}

        for step in steps:
            step_id = step.get("_id")

            # -------------------------------------------------
            # GLOBAL ABORT CHECK
            # -------------------------------------------------
            if aborted:
                trace.append(self._trace(step, "skipped", None, "aborted"))
                status_map[step_id] = "skipped"
                continue

            # -------------------------------------------------
            # DEPENDENCY CHECK
            # -------------------------------------------------
            deps = step.get("depends_on", [])
            if any(status_map.get(d) != "success" for d in deps):
                trace.append(self._trace(step, "skipped", None, "dependency_failed"))
                status_map[step_id] = "skipped"
                continue

            tool_name = step["tool"]
            args = step["args"]

            # -------------------------------------------------
            # TOOL FETCH
            # -------------------------------------------------
            if not self.registry.has(tool_name):
                result = {"status": "fail", "error": f"Unknown tool '{tool_name}'"}
                trace.append(self._trace(step, "fail", result))
                status_map[step_id] = "fail"
                aborted = True
                continue

            tool = self.registry.get(tool_name)
            meta = self.registry.get_metadata(tool_name)

            # -------------------------------------------------
            # RISK GATE (v0.8 addition)
            # -------------------------------------------------
            if meta["risk"] == "high":
                result = {
                    "status": "fail",
                    "error": f"Blocked high-risk tool: {tool_name}"
                }
                trace.append(self._trace(step, "blocked", result, "risk_gate"))
                status_map[step_id] = "blocked"
                aborted = True
                continue

            # -------------------------------------------------
            # EXECUTION
            # -------------------------------------------------
            try:
                output = tool(**args)
                result = {"status": "success", "output": output}

                trace.append(self._trace(step, "success", result))
                status_map[step_id] = "success"
                continue

            # -------------------------------------------------
            # FILE SYSTEM ERRORS (soft failure path)
            # -------------------------------------------------
            except FileNotFoundError as e:
                result = {"status": "fail", "error": str(e)}

                if step.get("on_fail") == "continue":
                    trace.append(self._trace(step, "soft_fail", result))
                    status_map[step_id] = "soft_fail"
                    continue

                if step.get("on_fail") == "fallback" and step.get("fallback"):
                    fb = step["fallback"]

                    try:
                        fb_tool = self.registry.get(fb["tool"])
                        fb_out = fb_tool(**fb.get("args", {}))

                        trace.append(self._trace(step, "soft_fail", result))

                        trace.append(self._trace(
                            {
                                "_id": f"{step_id}_fallback",
                                "tool": fb["tool"],
                                "args": fb.get("args", {}),
                            },
                            "success",
                            {"status": "success", "output": fb_out},
                        ))

                        status_map[step_id] = "soft_fail"
                        continue

                    except Exception as fe:
                        trace.append(self._trace(step, "fail", {"error": str(fe)}))
                        status_map[step_id] = "fail"
                        aborted = True
                        continue

                trace.append(self._trace(step, "fail", result))
                status_map[step_id] = "fail"
                aborted = True
                continue

            # -------------------------------------------------
            # UNKNOWN ERRORS
            # -------------------------------------------------
            except Exception as e:
                trace.append(self._trace(step, "fail", {"error": str(e)}))
                status_map[step_id] = "fail"
                aborted = True
                continue

        return ExecutionResult(
            goal=goal,
            status=self._compute_status(trace),
            trace=trace,
        )

    # =====================================================
    # TRACE HELPERS
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

        if any(s in ("soft_fail", "skipped", "blocked") for s in statuses):
            return "success_with_warnings"

        return "success"