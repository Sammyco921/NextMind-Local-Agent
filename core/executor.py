from core.errors import success, fail, fatal


class Executor:

    def __init__(self, registry):
        self.registry = registry

    # ====================================================
    # MAIN ENTRY
    # ====================================================

    def run(self, step: dict):

        # ----------------------------------------
        # STRUCTURE VALIDATION (STRICT)
        # ----------------------------------------
        if not isinstance(step, dict):
            return fatal("Step must be a dict", step)

        tool_name = step.get("tool")
        args = step.get("args", {})

        if not tool_name:
            return fatal("Missing tool name", step)

        if not isinstance(args, dict):
            return fatal("Tool args must be a dict", step)

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
        # OPTIONAL SAFETY: EMPTY STRING GUARD
        # ----------------------------------------
        for k, v in args.items():
            if isinstance(v, str) and v.strip() == "":
                return fatal(f"Empty string argument: {k}", step)

        # ----------------------------------------
        # EXECUTION (TRUST TOOL IMPLEMENTATION)
        # ----------------------------------------
        try:
            output = func(**args)

            return success(output=output, step=step)

        # ----------------------------------------
        # COMMON PYTHON ERRORS (EXPECTED FAILURES)
        # ----------------------------------------
        except TypeError as e:
            return fatal(f"Argument mismatch: {str(e)}", step)

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
        # GENERIC FAILURE (LAST RESORT)
        # ----------------------------------------
        except Exception as e:
            return fatal(f"Execution error: {str(e)}", step)
