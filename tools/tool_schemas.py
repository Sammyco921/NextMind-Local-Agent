"""
NextMind Tool Schemas (v1 - strict contract layer)

Design goals:
- Single source of truth for ALL tool arguments
- No naming ambiguity (filename ≠ file_name)
- Must match Python function signatures EXACTLY
- Planner + Executor must rely on this file
"""

from typing import Dict, Any, List


# =====================================================
# TOOL SCHEMA REGISTRY
# =====================================================

TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {

    # -------------------------------------------------
    # WRITE FILE
    # -------------------------------------------------
    "write_file": {
        "args": {
            "filename": "str",
            "content": "str"
        },
        "required": ["filename", "content"]
    },

    # -------------------------------------------------
    # READ FILE
    # -------------------------------------------------
    "read_file": {
        "args": {
            "filename": "str"
        },
        "required": ["filename"]
    },

    # -------------------------------------------------
    # LIST DIRECTORY
    # -------------------------------------------------
    "list_dir": {
        "args": {},
        "required": []
    }
}


# =====================================================
# VALIDATION HELPERS
# =====================================================

def is_valid_tool(tool_name: str) -> bool:
    """
    Check if tool exists in schema registry.
    """
    return tool_name in TOOL_SCHEMAS


def get_schema(tool_name: str) -> Dict[str, Any] | None:
    """
    Return full schema for a tool.
    """
    return TOOL_SCHEMAS.get(tool_name)


def get_required_args(tool_name: str) -> List[str] | None:
    """
    Return required arguments for a tool.
    """
    schema = TOOL_SCHEMAS.get(tool_name)
    if not schema:
        return None
    return schema.get("required", [])


def get_allowed_args(tool_name: str) -> List[str] | None:
    """
    Return ALL allowed argument keys for a tool.
    """
    schema = TOOL_SCHEMAS.get(tool_name)
    if not schema:
        return None
    return list(schema.get("args", {}).keys())


def validate_tool_call(tool_name: str, args: dict) -> None:
    """
    STRICT validation for tool calls.

    Raises ValueError if invalid.

    This is the most important safety function in the system.
    """

    if tool_name not in TOOL_SCHEMAS:
        raise ValueError(f"Unknown tool: {tool_name}")

    schema = TOOL_SCHEMAS[tool_name]
    required = schema.get("required", [])
    allowed = set(schema.get("args", {}).keys())

    # -------------------------------------------------
    # Check required arguments
    # -------------------------------------------------
    for key in required:
        if key not in args:
            raise ValueError(f"Missing required argument: {key}")

    # -------------------------------------------------
    # Reject unknown arguments (CRITICAL)
    # -------------------------------------------------
    for key in args:
        if key not in allowed:
            raise ValueError(f"Unexpected argument: {key}")

    return True


def get_tool_spec_for_prompt() -> str:
    """
    Converts schemas into a strict LLM prompt format.

    This prevents planner hallucination.
    """

    lines = []

    for tool, spec in TOOL_SCHEMAS.items():
        lines.append(f"{tool}:")

        args = spec.get("args", {})
        required = spec.get("required", [])

        if not args:
            lines.append("  args: NONE")
        else:
            lines.append("  args:")

            for arg, arg_type in args.items():
                req = "required" if arg in required else "optional"
                lines.append(f"    - {arg} ({arg_type}, {req})")

        lines.append("")

    return "\n".join(lines)
