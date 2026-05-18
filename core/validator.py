class Verifier:

    def __init__(self):
        pass

    # ====================================================
    # MAIN ENTRY
    # ====================================================

    def verify_step(self, state, step, result):

        # ------------------------------------------------
        # HARD FAIL SAFETY
        # ------------------------------------------------
        if not isinstance(result, dict):
            return {"status": "skip"}

        if result.get("status") != "success":
            return {"status": "skip"}

        tool = step.get("tool")
        history = state.get("history", [])

        # ------------------------------------------------
        # 1. PREVENT READ LOOP AFTER WRITE LOOP SPAM
        # ------------------------------------------------
        if tool == "read_file":

            if not history:
                return {"status": "pass"}

            prev = history[-1]
            prev_step = prev.get("step", {})
            prev_result = prev.get("result", {})

            if prev_step.get("tool") == "write_file":

                expected = prev_step.get("args", {}).get("content")
                actual = result.get("output", {}).get("content")

                if expected and actual != expected:
                    return {
                        "status": "fail",
                        "reason": "Read-after-write mismatch",
                        "expected": expected,
                        "actual": actual
                    }

        # ------------------------------------------------
        # 2. DETECT LOOPING BEHAVIOR (soft signal)
        # ------------------------------------------------
        if len(history) >= 3:

            last_tools = [h["step"]["tool"] for h in history[-3:]]

            if last_tools == ["write_file", "read_file", "write_file"]:
                return {
                    "status": "fail",
                    "reason": "Repetitive write/read loop detected"
                }

        # ------------------------------------------------
        # 3. GOAL-AWARE LIGHT CHECK (IMPORTANT)
        # ------------------------------------------------
        goal = state.get("goal", "").lower()
        output = result.get("output", {})

        if "summary" in goal and tool == "write_file":

            content = step.get("args", {}).get("content", "")

            if not content or len(content) < 5:
                return {
                    "status": "fail",
                    "reason": "Empty or invalid summary content"
                }

        # ------------------------------------------------
        # DEFAULT PASS
        # ------------------------------------------------
        return {"status": "pass"}