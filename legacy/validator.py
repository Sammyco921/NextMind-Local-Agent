from typing import Dict, Any, List

from tools.tool_registry import ToolRegistry


class ValidationResult:
    """
    Standardized validation response object.

    Rules:
    - Validation NEVER raises exceptions
    - Validation ALWAYS returns structured output
    """

    def __init__(
        self,
        allowed: bool,
        errors: List[str] = None,
        warnings: List[str] = None
    ):
        self.allowed = allowed
        self.errors = errors or []
        self.warnings = warnings or []

    def to_dict(self):

        return {
            "allowed": self.allowed,
            "errors": self.errors,
            "warnings": self.warnings
        }


class Validator:
    """
    v0.9 Deterministic Contract Validator

    Responsibilities:
    - Validate plans
    - Validate steps
    - Validate tool schemas
    - Enforce execution contracts

    Non-goals:
    - No execution
    - No correction
    - No auto-repair
    - No mutation of planner output
    """

    def __init__(self, registry: ToolRegistry):

        self.registry = registry

    # =====================================================
    # PLAN VALIDATION
    # =====================================================

    def validate_plan(
        self,
        plan: List[Dict[str, Any]]
    ) -> ValidationResult:

        errors = []
        warnings = []

        # -------------------------------------------------
        # PLAN TYPE
        # -------------------------------------------------

        if not isinstance(plan, list):
            return ValidationResult(
                allowed=False,
                errors=["plan must be list"]
            )

        # -------------------------------------------------
        # EMPTY PLAN
        # -------------------------------------------------

        if len(plan) == 0:
            return ValidationResult(
                allowed=False,
                errors=["plan is empty"]
            )

        # -------------------------------------------------
        # STEP VALIDATION
        # -------------------------------------------------

        for index, step in enumerate(plan):

            result = self.validate_step(step, index)

            if not result.allowed:
                errors.extend(result.errors)

            warnings.extend(result.warnings)

        return ValidationResult(
            allowed=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    # =====================================================
    # STEP VALIDATION
    # =====================================================

    def validate_step(
        self,
        step: Dict[str, Any],
        index: int = 0
    ) -> ValidationResult:

        errors = []
        warnings = []

        # -------------------------------------------------
        # TYPE CHECK
        # -------------------------------------------------

        if not isinstance(step, dict):
            return ValidationResult(
                allowed=False,
                errors=[f"step {index}: step must be dict"]
            )

        # -------------------------------------------------
        # REQUIRED FIELDS
        # -------------------------------------------------

        required_fields = [
            "tool",
            "args",
            "on_fail",
            "meta"
        ]

        for field in required_fields:

            if field not in step:
                errors.append(
                    f"step {index}: missing field '{field}'"
                )

        if errors:
            return ValidationResult(
                allowed=False,
                errors=errors
            )

        # -------------------------------------------------
        # FIELD EXTRACTION
        # -------------------------------------------------

        tool = step["tool"]
        args = step["args"]
        meta = step["meta"]

        # -------------------------------------------------
        # TOOL VALIDATION
        # -------------------------------------------------

        if not isinstance(tool, str):
            errors.append(
                f"step {index}: tool must be string"
            )

        elif not self.registry.has(tool):
            errors.append(
                f"step {index}: unknown tool '{tool}'"
            )

        # -------------------------------------------------
        # ARGS VALIDATION
        # -------------------------------------------------

        if not isinstance(args, dict):
            errors.append(
                f"step {index}: args must be dict"
            )

        # -------------------------------------------------
        # META VALIDATION
        # -------------------------------------------------

        if not isinstance(meta, dict):
            errors.append(
                f"step {index}: meta must be dict"
            )

        else:

            if "index" not in meta:
                errors.append(
                    f"step {index}: meta missing 'index'"
                )

        # -------------------------------------------------
        # STOP EARLY IF STRUCTURE BROKEN
        # -------------------------------------------------

        if errors:
            return ValidationResult(
                allowed=False,
                errors=errors
            )

        # -------------------------------------------------
        # SCHEMA VALIDATION
        # -------------------------------------------------

        schema_result = self._validate_schema(
            tool=tool,
            args=args,
            index=index
        )

        errors.extend(schema_result.errors)
        warnings.extend(schema_result.warnings)

        return ValidationResult(
            allowed=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    # =====================================================
    # SCHEMA VALIDATION
    # =====================================================

    def _validate_schema(
        self,
        tool: str,
        args: Dict[str, Any],
        index: int
    ) -> ValidationResult:

        errors = []
        warnings = []

        schema = self.registry.get_schema(tool)

        # -------------------------------------------------
        # SCHEMA EXISTS
        # -------------------------------------------------

        if schema is None:
            return ValidationResult(
                allowed=False,
                errors=[
                    f"step {index}: missing schema for '{tool}'"
                ]
            )

        # -------------------------------------------------
        # REQUIRED SCHEMA FIELDS
        # -------------------------------------------------

        for field, expected_type in schema.items():

            if field not in args:
                errors.append(
                    f"step {index}: missing arg '{field}'"
                )
                continue

            value = args[field]

            # ---------------------------------------------
            # STRING
            # ---------------------------------------------

            if expected_type == "string":

                if not isinstance(value, str):
                    errors.append(
                        f"step {index}: '{field}' must be string"
                    )

            # ---------------------------------------------
            # INT
            # ---------------------------------------------

            elif expected_type == "int":

                if not isinstance(value, int):
                    errors.append(
                        f"step {index}: '{field}' must be int"
                    )

            # ---------------------------------------------
            # LIST
            # ---------------------------------------------

            elif expected_type == "list":

                if not isinstance(value, list):
                    errors.append(
                        f"step {index}: '{field}' must be list"
                    )

            # ---------------------------------------------
            # DICT
            # ---------------------------------------------

            elif expected_type == "dict":

                if not isinstance(value, dict):
                    errors.append(
                        f"step {index}: '{field}' must be dict"
                    )

            # ---------------------------------------------
            # UNKNOWN TYPE
            # ---------------------------------------------

            else:

                errors.append(
                    f"step {index}: unknown schema type '{expected_type}'"
                )

        # -------------------------------------------------
        # EXTRA ARG DETECTION
        # -------------------------------------------------

        for field in args.keys():

            if field not in schema:

                warnings.append(
                    f"step {index}: unexpected arg '{field}'"
                )

        return ValidationResult(
            allowed=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )