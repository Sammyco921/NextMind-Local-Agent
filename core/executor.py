class Executor:

    def __init__(self, registry, critic=None):

        self.registry = registry
        self.critic = critic

    # ====================================================
    # MAIN EXECUTION
    # ====================================================

    def run(self, step: dict):

        tool_name = step.get("tool")
        args = step.get("args", {})

        # --------------------------------------------
        # TOOL LOOKUP
        # --------------------------------------------
        try:
            tool = self.registry.get(tool_name)

        except Exception as e:
            return {
                "status": "fatal_error",
                "error": str(e),
                "step": step
            }

        # --------------------------------------------
        # EXTRACT FUNCTION
        # --------------------------------------------
        func = tool.get("func")

        if not callable(func):

            return {
                "status": "fatal_error",
                "error": f"Tool not callable: {tool_name}",
                "step": step
            }

        # --------------------------------------------
        # EXECUTION
        # --------------------------------------------
        try:

            output = func(**args)

            return {
                "status": "success",
                "output": output,
                "step": step
            }

        except TypeError as e:

            return {
                "status": "fatal_error",
                "error": f"Argument mismatch: {str(e)}",
                "step": step
            }

        except Exception as e:

            return {
                "status": "fatal_error",
                "error": str(e),
                "step": step
            }
