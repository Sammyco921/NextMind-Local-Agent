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
    "__inject_failure__": {
        "failure_type": str,
    },
}

# Public registry alias (roadmap contract)
TOOL_REGISTRY: Dict[str, ToolSchemaEntry] = TOOL_SCHEMAS


def get_tool(name: str) -> ToolSchemaEntry:
    if name not in TOOL_SCHEMAS:
        raise ValueError(f"Unknown tool: {name}")
    return TOOL_SCHEMAS[name]


def validate_tool_call(tool_name: str, args: Dict[str, Any]) -> bool:
    """
    Validate a tool invocation against TOOL_SCHEMAS.
    Returns True on success, raises ValueError on failure.
    """
    if tool_name not in TOOL_SCHEMAS:
        raise ValueError(f"Unknown tool: {tool_name}")

    if not isinstance(args, dict):
        raise ValueError("Args must be a dictionary")

    schema = TOOL_SCHEMAS[tool_name]

    for key in schema:
        if key not in args:
            raise ValueError(f"Missing required argument: {key}")

    for key in args:
        if key not in schema:
            raise ValueError(f"Unexpected argument: {key}")

    for key, expected_type in schema.items():
        value = args[key]
        if not isinstance(value, expected_type):
            raise ValueError(
                f"Argument '{key}' expected {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )
        if isinstance(value, str) and value.strip() == "":
            raise ValueError(f"Argument '{key}' cannot be empty string")

    return True


def required_args(tool_name: str) -> List[str]:
    return list(TOOL_SCHEMAS.get(tool_name, {}).keys())
