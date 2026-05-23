# core/contracts.py

from typing import Dict, Any


# ====================================================
# EXECUTOR CONTRACT
# ====================================================

EXECUTOR_RESPONSE_SCHEMA = {
    "status": str,
    "output": (dict, type(None)),
    "error": (str, type(None)),
    "step": dict,
}


# ====================================================
# TOOL STEP CONTRACT
# ====================================================

TOOL_STEP_SCHEMA = {
    "id": str,
    "tool": str,
    "args": dict,
}


# ====================================================
# PLANNER OUTPUT CONTRACT
# ====================================================

PLANNER_OUTPUT_SCHEMA = {
    "steps": list,
}


# ====================================================
# GOAL MODEL CONTRACT
# ====================================================

GOAL_MODEL_SCHEMA = {
    "intent": str,
    "entities": dict,
    "raw": str,
}


# ====================================================
# TOOL REGISTRY CONTRACT
# ====================================================

TOOL_REGISTRY_SCHEMA = {
    "name": str,
    "func": object,
    "description": str,
    "schema": dict,
}


# ====================================================
# CONTRACT VALIDATION ENGINE
# ====================================================

def validate_contract(
    obj: Dict[str, Any],
    schema: Dict[str, Any],
    name: str = "Contract"
) -> None:
    """
    Lightweight deterministic schema validator.

    Raises:
        ValueError
        TypeError
    """

    if not isinstance(obj, dict):
        raise TypeError(f"{name}: object must be dict")

    # ---------------------------------------------
    # Missing keys
    # ---------------------------------------------

    for key in schema:

        if key not in obj:
            raise ValueError(
                f"{name}: missing key '{key}'"
            )

    # ---------------------------------------------
    # Type validation
    # ---------------------------------------------

    for key, expected_type in schema.items():

        value = obj[key]

        if not isinstance(value, expected_type):

            # tuple support
            if isinstance(expected_type, tuple):

                valid = any(
                    isinstance(value, t)
                    for t in expected_type
                )

                if not valid:
                    raise TypeError(
                        f"{name}: key '{key}' invalid type "
                        f"(expected {expected_type}, got {type(value)})"
                    )

            else:

                raise TypeError(
                    f"{name}: key '{key}' expected "
                    f"{expected_type.__name__}, got "
                    f"{type(value).__name__}"
                )