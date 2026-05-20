class Critic:

    def __init__(self, valid_tools=None):
        self.valid_tools = set(valid_tools or [])

    # ====================================================
    # MAIN ENTRY
    # ====================================================

    def evaluate_step(self, step: dict, result: dict):

        # ----------------------------------------
        # STRUCTURE VALIDATION (STRICT)
        # ----------------------------------------
        if not isinstance(step, dict):
            return self._fail(
                "Invalid step format",
                "Step must be a dict"
            )

        if not isinstance(result, dict):
            return self._fail(
                "Invalid executor output",
                "Result must be a dict"
            )

        tool = step.get("tool")

        # ----------------------------------------
        # TOOL VALIDATION (OPTIONAL SAFETY LAYER)
        # ----------------------------------------
        if self.valid_tools and tool not in self.valid_tools:
            return self._fail(
                "Unknown tool used",
                f"Tool '{tool}' not allowed"
            )

        # ----------------------------------------
        # STATUS CHECK (SINGLE SOURCE OF TRUTH)
        # ----------------------------------------
        status = result.get("status")

        if status != "success":
            return self._fail(
                result.get("error") or "Execution failed",
                self._suggest_fix(tool, result)
            )

        output = result.get("output")

        # ----------------------------------------
        # TOOL-SPECIFIC OUTPUT VALIDATION
        # ----------------------------------------

        if tool == "write_file":
            return self._check_write_file(output)

        if tool == "read_file":
            return self._check_read_file(output)

        if tool == "list_dir":
            return self._check_list_dir(output)

        # ----------------------------------------
        # DEFAULT PASS
        # ----------------------------------------
        return {
            "status": "pass",
            "tool": tool,
            "reason": None
        }

    # ====================================================
    # WRITE FILE VALIDATION
    # ====================================================

    def _check_write_file(self, output):

        if not isinstance(output, dict):
            return self._fail(
                "Invalid write_file output",
                "Expected dict return from tool"
            )

        if "file" not in output:
            return self._fail(
                "Malformed write_file output",
                "Missing 'file' key"
            )

        return {"status": "pass"}

    # ====================================================
    # READ FILE VALIDATION
    # ====================================================

    def _check_read_file(self, output):

        if not isinstance(output, dict):
            return self._fail(
                "Invalid read_file output",
                "Expected dict return from tool"
            )

        if "content" not in output:
            return self._fail(
                "Malformed read_file output",
                "Missing 'content' key"
            )

        return {"status": "pass"}

    # ====================================================
    # LIST DIR VALIDATION
    # ====================================================

    def _check_list_dir(self, output):

        if not isinstance(output, dict):
            return self._fail(
                "Invalid list_dir output",
                "Expected dict return from tool"
            )

        if "items" not in output:
            return self._fail(
                "Malformed list_dir output",
                "Missing 'items' key"
            )

        return {"status": "pass"}

    # ====================================================
    # FIX SUGGESTION (LIGHTWEIGHT, NON-OVERREACHING)
    # ====================================================

    def _suggest_fix(self, tool, result):

        error = result.get("error")

        if not error:
            return "Check executor and tool implementation"

        error = str(error).lower()

        if "not found" in error:
            return "Ensure file or path exists before operation"

        if "permission" in error:
            return "Check filesystem permissions"

        if tool == "write_file":
            return "Verify filename and content are valid strings"

        if tool == "read_file":
            return "Ensure file exists before reading"

        return "Inspect execution pipeline and tool contract"

    # ====================================================
    # STANDARD FAIL FORMAT
    # ====================================================

    def _fail(self, reason, fix):

        return {
            "status": "fail",
            "reason": reason,
            "fix": fix
        }