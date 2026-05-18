class Executor:

    def __init__(self, registry):
        self.registry = registry

    # ====================================================
    # MAIN ENTRY
    # ====================================================

    def run(self, step: dict):

        # ----------------------------------------
        # BASIC VALIDATION
        # ----------------------------------------
        if not isinstance(step, dict):
            return fatal("Step must be dict", step)

        tool_name = step.get("tool")
        args = step.get("args", {})

        if not tool_name:
            return fatal("Missing tool name", step)

        if not isinstance(args, dict):
            return fatal("Tool args must be dict", step)

        # ----------------------------------------
        # TOOL LOOKUP
        # ----------------------------------------
        try:
            tool = self.registry.get(tool_name)
        except Exception as e:
            return fatal(str(e), step)

        func = tool.get("func")

        if not callable(func):
            return fatal(f"Tool not callable: {tool_name}", step)

        # ----------------------------------------
        # EXECUTION
        # ----------------------------------------
        try:
            output = func(**args)

            return success(output=output, step=step)

        # ----------------------------------------
        # ARGUMENT ERRORS (BUG CLASS)
        # ----------------------------------------
        except TypeError as e:
            return fatal(f"Argument mismatch: {str(e)}", step)

        # ----------------------------------------
        # FILE / RUNTIME ERRORS (EXPECTED FAILURES)
        # ----------------------------------------
        except FileNotFoundError as e:
            return fail(
                reason=str(e),
                fix="Ensure file exists before operation",
                step=step
            )

        except PermissionError as e:
            return fail(
                reason=str(e),
                fix="Check filesystem permissions",
                step=step
            )

        # ----------------------------------------
        # GENERIC FALLBACK
        # ----------------------------------------
        except Exception as e:
            return fatal(f"Unknown execution error: {str(e)}", step)
