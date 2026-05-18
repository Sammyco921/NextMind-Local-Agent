from typing import Dict, Any, List
from state.schema import Step, StepResult


class ValidationError(Exception):
    pass


# ====================================================
# VALIDATOR
# ====================================================

class Validator:

    def __init__(self, tool_schemas: Dict[str, Dict[str, Any]]):
        self.tool_schemas = tool_schemas

    # ====================================================
    # STEP VALIDATION
    # ====================================================

    def validate_step(self, step: Dict[str, Any]) -> Step:
        if not isinstance(step, dict):
            raise ValidationError("Step must be a dict")

        tool = step.get("tool")
        args = step.get("args")

        if not isinstance(tool, str) or not tool.strip():
            raise ValidationError("Missing or invalid tool name")

        if not isinstance(args, dict):
            raise ValidationError("Args must be a dict")

        tool = tool.strip()

        if tool not in self.tool_schemas:
            raise ValidationError(f"Unknown tool: {tool}")

        schema = self.tool_schemas[tool]
        required = schema.get("required", [])
        allowed = set(schema.get("args", {}).keys())

        # ----------------------------
        # REQUIRED ARG CHECK
        # ----------------------------
        for key in required:
            if key not in args:
                raise ValidationError(f"Missing required arg: {key}")

        # ----------------------------
        # UNKNOWN ARG CHECK
        # ----------------------------
        for key in args:
            if key not in allowed:
                raise ValidationError(f"Unexpected arg: {key}")

        # ----------------------------
        # EMPTY STRING CHECK (IMPORTANT)
        # ----------------------------
        for k, v in args.items():
            if isinstance(v, str) and not v.strip():
                raise ValidationError(f"Empty string not allowed for '{k}'")

        return Step(
            id=step.get("id", 0),
            tool=tool,
            args=args
        )

    # ====================================================
    # RESULT VALIDATION
    # ====================================================

    def validate_result(self, result: Dict[str, Any]) -> StepResult:
        if not isinstance(result, dict):
            raise ValidationError("Result must be dict")

        status = result.get("status")

        if status not in ["success", "fail", "fatal_error"]:
            raise ValidationError(f"Invalid status: {status}")

        return StepResult(
            status=status,
            output=result.get("output"),
            error=result.get("error"),
            fix=result.get("fix"),
            step=result.get("step")
        )

    # ====================================================
    # SAFE WRAPPERS
    # ====================================================

    def safe_validate_step(self, step: Dict[str, Any]):
        try:
            return self.validate_step(step)
        except ValidationError as e:
            return None, str(e)

    def safe_validate_result(self, result: Dict[str, Any]):
        try:
            return self.validate_result(result)
        except ValidationError as e:
            return None, str(e)
