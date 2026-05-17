import json
from tools.tool_registry import TOOL_REGISTRY


class Executor:
    """
    Executes individual task steps using registered tools.
    """

    def __init__(self):
        pass

    def execute(self, step: dict) -> dict:
        """
        Execute a single planned step.

        Expected step format:
        {
            "id": 1,
            "tool": "write_file",
            "args": {
                ...
            }
        }

        Returns:
            dict: Execution result
        """

        step_id = step.get("id")
        tool_name = step.get("tool")
        args = step.get("args", {})

        # --------------------------------------------------------
        # Validate tool existence
        # --------------------------------------------------------

        if tool_name not in TOOL_REGISTRY:
            return {
                "step_id": step_id,
                "status": "fail",
                "output": None,
                "error": f"Tool '{tool_name}' is not registered."
            }

        tool_function = TOOL_REGISTRY[tool_name]

        # --------------------------------------------------------
        # Execute tool safely
        # --------------------------------------------------------

        try:
            result = tool_function(**args)

            return {
                "step_id": step_id,
                "status": "success",
                "output": result,
                "error": None
            }

        except Exception as e:
            return {
                "step_id": step_id,
                "status": "fail",
                "output": None,
                "error": str(e)
            }
