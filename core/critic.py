class Critic:

    def __init__(self, valid_tools=None):
        self.valid_tools = set(valid_tools or [])

    # ====================================================
    # MAIN ENTRY
    # ====================================================

    def evaluate_step(self, step: dict, result: dict):

        if not isinstance(step, dict):
            return self._fail("Invalid step format", "Step must be dict")

        if not isinstance(result, dict):
            return self._fail("Invalid executor output", "Result must be dict")

        tool = step.get("tool")
        args = step.get("args", {})

        # ------------------------------------------------
        # TOOL VALIDATION (light, not authoritative)
        # ------------------------------------------------
        if self.valid_tools and tool not in self.valid_tools:
            return self._fail(
                "Unknown tool used",
                f"Tool '{tool}' is not in allowed tool list"
            )

        # ------------------------------------------------
        # EXECUTION STATUS CHECK
        # ------------------------------------------------
        status = result.get("status")

        if status != "success":
            return self._fail(
                result.get("error") or "Execution failed",
                self._suggest_fix(tool, result)
            )

        output = result.get("output")

        # ------------------------------------------------
        # TOOL-SPECIFIC CHECKS
        # ------------------------------------------------
        if tool == "write_file":
            return self._check_write_file(output)

        if tool == "read_file":
            return self._check_read_file(output)

        if tool == "list_dir":
            return self._check_list_dir(output)

        # ------------------------------------------------
        # DEFAULT PASS
        # ------------------------------------------------
        return {
            "status": "pass",
            "tool": tool,
            "step_id": step.get("id"),
            "reason": None
        }

    # ====================================================
    # WRITE FILE
    # ====================================================

    def _check_write_file(self, output):

        if not isinstance(output, dict):
            return self._fail(
                "Invalid output type",
                "write_file must return dict"
            )

        if "file" not in output:
            return self._fail(
                "Malformed write_file output",
                "Missing 'file' key"
            )

        return {"status": "pass"}

    # ====================================================
    # READ FILE
    # ====================================================

    def _check_read_file(self, output):

        if not isinstance(output, dict):
            return self._fail(
                "Invalid output type",
                "read_file must return dict"
            )

        if "content" not in output:
            return self._fail(
                "Malformed read_file output",
                "Missing 'content' key"
            )

        return {"status": "pass"}

    # ====================================================
    # LIST DIR
    # ====================================================

    def _check_list_dir(self, output):

        if not isinstance(output, dict):
            return self._fail(
                "Invalid output type",
                "list_dir must return dict"
            )

        if "items" not in output:
            return self._fail(
                "Malformed list_dir output",
                "Missing 'items' key"
            )

        return {"status": "pass"}

    # ====================================================
    # FIX SUGGESTION (SAFE + NON-HALLUCINATED)
    # ====================================================

    def _suggest_fix(self, tool, result):

        error = result.get("error")

        if not error:
            return "Check executor implementation and tool contract"

        error = str(error).lower()

        if "permission" in error:
            return "Check filesystem permissions"

        if "not found" in error:
            return "Ensure file or path exists before operation"

        if tool == "write_file":
            return "Validate filename and content arguments"

        if tool == "read_file":
            return "Ensure file exists before reading"

        return "Inspect executor + tool implementation"

    # ====================================================
    # STANDARD FAIL FORMAT
    # ====================================================

    def _fail(self, reason, fix):

        return {
            "status": "fail",
            "reason": reason,
            "fix": fix
        }
