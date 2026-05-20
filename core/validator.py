class Verifier:

    def __init__(self):
        pass

    # ====================================================
    # MAIN ENTRY
    # ====================================================

    def verify_step(self, state, step, result):

        # ------------------------------------------------
        # 0. HARD SAFETY CHECKS
        # ------------------------------------------------
        if not isinstance(result, dict):
            return {"status": "pass"}

        if result.get("status") == "fail":
            return {
                "status": "fail",
                "reason": result.get("error", "tool reported failure")
            }

        tool = step.get("tool")
        history = state.get("history", [])

        # ------------------------------------------------
        # 1. READ AFTER WRITE CONSISTENCY CHECK
        # ------------------------------------------------
        if tool == "read_file":

            if not history:
                return {"status": "pass"}

            prev = history[-1]
            prev_step = prev.get("step", {})
            prev_result = prev.get("result", {})

            if prev_step.get("tool") == "write_file":

                expected = prev_step.get("args", {}).get("content")

                actual = (
                    result.get("output", {}) or {}
                ).get("content")

                # ONLY compare if both exist
                if expected is not None and actual is not None:
                    if expected != actual:
                        return {
                            "status": "fail",
                            "reason": "Read-after-write mismatch",
                            "expected": expected,
                            "actual": actual
                        }

        # ------------------------------------------------
        # 2. LOOP DETECTION (SOFT SIGNAL ONLY)
        # ------------------------------------------------
        if len(history) >= 3:

            last_tools = [h["step"]["tool"] for h in history[-3:]]

            if last_tools == ["write_file", "read_file", "write_file"]:
                return {
                    "status": "fail",
                    "reason": "Repetitive write/read loop detected"
                }

        # ------------------------------------------------
        # 3. GOAL-AWARE LIGHT CHECK (SAFE)
        # ------------------------------------------------
        goal = state.get("goal", "").lower()

        if "summary" in goal and tool == "write_file":

            content = step.get("args", {}).get("content")

            if content is not None and len(content.strip()) < 5:
                return {
                    "status": "fail",
                    "reason": "Empty or invalid summary content"
                }

        # ------------------------------------------------
        # 4. DEFAULT PASS (IMPORTANT FIX)
        # ------------------------------------------------
        return {"status": "pass"}