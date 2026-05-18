from core.schema import TOOL_SCHEMAS


class Validator:

    # ====================================================
    # MAIN ENTRY
    # ====================================================

    def validate_step(self, step: dict) -> dict:

        if not isinstance(step, dict):
            return self._fail("Step must be a dictionary")

        tool = step.get("tool")
        args = step.get("args", {})

        # ---------------------------------------------
        # TOOL CHECK
        # ---------------------------------------------
        if not tool or not isinstance(tool, str):
            return self._fail("Missing or invalid tool name")

        if tool not in TOOL_SCHEMAS:
            return self._fail(f"Unknown tool: {tool}")

        schema = TOOL_SCHEMAS[tool]
        required = schema.get("required", [])
        allowed = set(schema.get("args", {}).keys())

        if not isinstance(args, dict):
            return self._fail("Arguments must be a dictionary")

        # ---------------------------------------------
        # REQUIRED ARGUMENTS
        # ---------------------------------------------
        for key in required:
            if key not in args:
                return self._fail(f"Missing required argument: {key}")

        # ---------------------------------------------
        # UNKNOWN ARGUMENTS
        # ---------------------------------------------
        for key in args:
            if key not in allowed:
                return self._fail(f"Unexpected argument: {key}")

        # ---------------------------------------------
        # EMPTY STRING GUARD (CRITICAL FIX)
        # ---------------------------------------------
        for key, value in args.items():
            if isinstance(value, str) and value.strip() == "":
                return self._fail(f"Argument '{key}' cannot be empty string")

        return {
            "status": "success",
            "step": step
        }

    # ====================================================
    # BATCH VALIDATION (useful for planner)
    # ====================================================

    def validate_plan(self, plan: dict) -> dict:

        if not isinstance(plan, dict):
            return self._fail("Plan must be a dictionary")

        steps = plan.get("steps")

        if not isinstance(steps, list):
            return self._fail("Plan must contain a list of steps")

        validated = []

        for step in steps:

            result = self.validate_step(step)

            if result["status"] == "fail":
                return result  # fail fast (strict mode)

            validated.append(result["step"])

        return {
            "status": "success",
            "steps": validated
        }

    # ====================================================
    # SAFE WRAPPER FOR EXECUTOR
    # ====================================================

    def precheck(self, step: dict):

        return self.validate_step(step)

    # ====================================================
    # INTERNAL FAIL FORMAT
    # ====================================================

    def _fail(self, reason: str):

        return {
            "status": "fail",
            "reason": reason
        }
