class Critic:

    def __init__(self, valid_tools=None):
        self.valid_tools = set(valid_tools or [])

    def evaluate_step(self, step: dict, result: dict):

        tool = step.get("tool")

        # -----------------------------------------
        # HARD FAILURE ONLY (executor crashed)
        # -----------------------------------------
        if not isinstance(result, dict):
            return {
                "status": "fail",
                "reason": "Non-dict executor output",
                "fix_suggestion": "Fix executor return contract"
            }

        if result.get("status") == "fatal_error":
            return {
                "status": "fail",
                "reason": result.get("error", "Executor crashed"),
                "fix_suggestion": self._suggest_fix(tool, result)
            }

        if result.get("status") != "success":
            return {
                "status": "fail",
                "reason": result.get("error", "Unknown failure"),
                "fix_suggestion": self._suggest_fix(tool, result)
            }

        output = result.get("output")

        # -----------------------------------------
        # TOOL VALIDATION
        # -----------------------------------------
        if tool == "write_file":
            if not isinstance(output, dict) or "file" not in output:
                return self._fail("write_file output invalid")

        if tool == "read_file":
            if not isinstance(output, dict) or "content" not in output:
                return self._fail("read_file output invalid")

        if tool == "list_dir":
            if not isinstance(output, dict) or "items" not in output:
                return self._fail("list_dir output invalid")

        return {
            "status": "pass",
            "reason": None
        }

    def _fail(self, msg):
        return {
            "status": "fail",
            "reason": msg,
            "fix_suggestion": "Fix tool implementation contract"
        }

    def _suggest_fix(self, tool, result):

        err = str(result.get("error", ""))

        if "argument" in err.lower():
            return "Fix planner args schema mismatch"

        if "unknown tool" in err.lower():
            return "Register tool in registry"

        return "Inspect executor + tool contract"
