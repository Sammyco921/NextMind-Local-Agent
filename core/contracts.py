# core/contracts.py


# ====================================================
# EXECUTOR CONTRACT
# ====================================================

EXECUTOR_RESPONSE_SCHEMA = {
    "status": "success | fail | fatal_error",
    "output": "dict | None",
    "error": "str | None",
    "step": "dict"
}


# ====================================================
# TOOL STEP CONTRACT
# ====================================================

TOOL_STEP_SCHEMA = {
    "id": "int",
    "tool": "str",
    "args": "dict"
}


# ====================================================
# PLANNER OUTPUT CONTRACT
# ====================================================

PLANNER_OUTPUT_SCHEMA = {
    "steps": [
        {
            "tool": "str",
            "args": "dict"
        }
    ]
}


# ====================================================
# GOAL MODEL CONTRACT (from intent_router)
# ====================================================

GOAL_MODEL_SCHEMA = {
    "intent": "str",
    "entities": "dict",
    "raw": "str"
}


# ====================================================
# TOOL REGISTRY ENTRY CONTRACT
# ====================================================

TOOL_REGISTRY_SCHEMA = {
    "name": "str",
    "func": "callable",
    "description": "str",
    "schema": "dict"
}