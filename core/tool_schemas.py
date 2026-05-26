# core/tool_schemas.py
#
# Single source of truth for tool argument contracts.

from __future__ import annotations

from typing import Any, Dict, List, Type

# Schema entry: arg_name -> Python type (empty dict = no args)
ToolSchemaEntry = Dict[str, Type[Any]]

TOOL_SCHEMAS: Dict[str, ToolSchemaEntry] = {
    "write_file": {
        "filename": str,
        "content": str,
    },
    "read_file": {
        "filename": str,
    },
    "list_dir": {
        "path": str,
    },
}

# Public registry alias (roadmap contract)
TOOL_REGISTRY: Dict[str, ToolSchemaEntry] = TOOL_SCHEMAS


def get_tool(name: str) -> ToolSchemaEntry:
    if name not in TOOL_SCHEMAS:
        raise ValueError(f"Unknown tool: {name}")
    return TOOL_SCHEMAS[name]


def validate_tool_call(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a tool invocation against TOOL_SCHEMAS.
    Returns {"status": "success"} or {"status": "fail", "reason": "..."}.
    """
    if tool_name not in TOOL_SCHEMAS:
        return {"status": "fail", "reason": f"Unknown tool: {tool_name}"}

    if not isinstance(args, dict):
        return {"status": "fail", "reason": "Args must be a dictionary"}

    schema = TOOL_SCHEMAS[tool_name]

    for key in schema:
        if key not in args:
            return {
                "status": "fail",
                "reason": f"Missing required argument: {key}",
            }

    for key in args:
        if key not in schema:
            return {
                "status": "fail",
                "reason": f"Unexpected argument: {key}",
            }

    for key, expected_type in schema.items():
        value = args[key]
        if not isinstance(value, expected_type):
            return {
                "status": "fail",
                "reason": (
                    f"Argument '{key}' expected {expected_type.__name__}, "
                    f"got {type(value).__name__}"
                ),
            }
        if isinstance(value, str) and value.strip() == "":
            return {
                "status": "fail",
                "reason": f"Argument '{key}' cannot be empty string",
            }

    return {"status": "success"}


def required_args(tool_name: str) -> List[str]:
    return list(TOOL_SCHEMAS.get(tool_name, {}).keys())
