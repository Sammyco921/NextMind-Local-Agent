class Executor:
    """
    Stable executor for NextMind v0.6
    - strict tool execution
    - safe argument passing
    - normalized outputs
    - no registry coupling hacks
    """

    def __init__(self, registry):
        self.registry = registry

    # ----------------------------------------------------
    # PUBLIC ENTRY
    # ----------------------------------------------------
    def execute(self, step: dict):
        tool_name = step.get("tool")
        args = step.get("args", {})

        if not tool_name:
            return self._fail("Missing tool name in step")

        if not isinstance(args, dict):
            return self._fail("Tool args must be a dict")

        # Validate tool exists (use stable API)
        if not self.registry.has(tool_name):
            return self._fail(f"Tool not found: {tool_name}")

        tool = self.registry.get(tool_name)

        try:
            result = tool(**args)
            return self._success(tool_name, result, step)

        except TypeError as e:
            # VERY IMPORTANT: catches wrong arg passing like your JSON bugs
            return self._fail(
                f"Tool argument mismatch for '{tool_name}': {str(e)}"
            )

        except Exception as e:
            return self._fail(
                f"Execution error in '{tool_name}': {str(e)}"
            )

    # ----------------------------------------------------
    # SUCCESS FORMAT
    # ----------------------------------------------------
    def _success(self, tool_name, output, step):
        return {
            "status": "success",
            "tool": tool_name,
            "output": output,
            "step": step
        }

    # ----------------------------------------------------
    # FAIL FORMAT (STANDARDIZED)
    # ----------------------------------------------------
    def _fail(self, message):
        return {
            "status": "fail",
            "error": message
        }