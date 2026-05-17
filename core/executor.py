from typing import Dict, Any


class Executor:
    """
    Schema-safe executor.

    Rules:
    - NEVER trust planner output
    - ToolRegistry is the ONLY authority
    - Fail fast on any mismatch
    """

    def __init__(self, tool_registry):
        self.tool_registry = tool_registry

    # ----------------------------------------------------
    # EXECUTE SINGLE STEP
    # ----------------------------------------------------
    def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:

        tool_name = step.get("tool")
        args = step.get("args", {})

        # -----------------------------
        # 1. TOOL EXISTS CHECK
        # -----------------------------
        if tool_name not in self.tool_registry.tools:
            return {
                "status": "fail",
                "output": None,
                "error": f"Unknown tool: {tool_name}"
            }

        tool_meta = self.tool_registry.tools[tool_name]
        schema = tool_meta["args_schema"]

        # -----------------------------
        # 2. STRICT ARG VALIDATION
        # -----------------------------
        try:
            self.tool_registry.validate_args(tool_name, args)
        except Exception as e:
            return {
                "status": "fail",
                "output": None,
                "error": f"Schema validation failed: {str(e)}"
            }

        # -----------------------------
        # 3. EXECUTE TOOL
        # -----------------------------
        try:
            func = tool_meta["func"]
            result = func(**args)

            return {
                "status": "success",
                "output": result,
                "error": None
            }

        except Exception as e:
            return {
                "status": "fail",
                "output": None,
                "error": f"Execution error: {str(e)}"
            }

    # ----------------------------------------------------
    # OPTIONAL: BATCH EXECUTION SUPPORT
    # ----------------------------------------------------
    def execute_plan(self, plan: Dict[str, Any]):

        results = []

        for step in plan.get("steps", []):
            result = self.execute_step(step)
            results.append({
                "step": step,
                "result": result
            })

        return results
