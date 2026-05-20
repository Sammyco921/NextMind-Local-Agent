class Orchestrator:
    """
    Stable Orchestrator v0.6.x (safe execution hardened)

    Fixes:
    - prevents error-output contamination into tool args
    - keeps soft-fail behavior
    - normalizes execution results
    """

    def __init__(self, planner, executor, memory_manager=None):
        self.planner = planner
        self.executor = executor
        self.memory_manager = memory_manager

    # ====================================================
    # MAIN RUN LOOP
    # ====================================================
    def run(self, goal: str):
        steps = self.planner.plan(goal)

        history = []
        executed = 0

        # shared safe context (IMPORTANT FIX)
        context = {
            "goal": goal,
            "last_success": None,
            "failures": [],
        }

        for step in steps:
            safe_step = self._sanitize_step(step, context)

            result = self._execute_step(safe_step)

            history.append({
                "step": safe_step,
                "result": result
            })

            executed += 1

            # update context safely
            if result.get("status") == "success":
                context["last_success"] = result

            elif result.get("status") in ("fail", "soft_fail"):
                context["failures"].append(result)

        self._store_memory_safe(goal, history)

        return {
            "goal": goal,
            "status": self._compute_status(history),
            "steps_executed": executed,
            "history": history
        }

    # ====================================================
    # 🔒 CRITICAL FIX: sanitize step input
    # ====================================================
    def _sanitize_step(self, step, context):
        """
        Prevents planner/executor corruption:
        - strips error text injection
        - blocks invalid tool args
        """

        safe_step = {
            "tool": step.get("tool"),
            "args": step.get("args", {}).copy()
        }

        # ❌ REMOVE any accidental error injection fields
        for k in list(safe_step["args"].keys()):
            v = safe_step["args"][k]

            if isinstance(v, str):
                # block raw traceback leakage
                if "Traceback" in v or "Error" in v or "FileNotFoundError" in v:
                    safe_step["args"][k] = ""

        return safe_step

    # ====================================================
    # EXECUTION
    # ====================================================
    def _execute_step(self, step):
        try:
            result = self.executor.execute(step)

            # soft-fail normalization (missing file safe path)
            if result.get("status") == "fail":
                if step.get("tool") == "read_file":
                    return {
                        "status": "soft_fail",
                        "tool": "read_file",
                        "error": result.get("error"),
                        "step": step
                    }

            return result

        except Exception as e:
            return {
                "status": "fail",
                "error": str(e),
                "step": step
            }

    # ====================================================
    # STATUS ENGINE
    # ====================================================
    def _compute_status(self, history):
        if not history:
            return "fail"

        has_fail = False
        has_soft_fail = False

        for item in history:
            status = item["result"].get("status")

            if status == "fail":
                has_fail = True
            elif status == "soft_fail":
                has_soft_fail = True

        if has_fail:
            return "partial_failure"

        if has_soft_fail:
            return "success_with_warnings"

        return "success"

    # ====================================================
    # MEMORY SAFE
    # ====================================================
    def _store_memory_safe(self, goal, history):
        if not self.memory_manager:
            return

        try:
            payload = {
                "goal": goal,
                "history": history
            }

            if hasattr(self.memory_manager, "store"):
                self.memory_manager.store(payload)
            elif hasattr(self.memory_manager, "add"):
                self.memory_manager.add(goal, history)

        except Exception:
            pass