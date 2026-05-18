"""
NextMind Tool Schemas (v1 - strict contract layer)

Design goals:
- Single source of truth for ALL tool arguments
- Must match Python function signatures EXACTLY
- No naming ambiguity allowed
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
        "args": {
            "path": "str"
        },
        "required": []
    }
}


# =====================================================
# VALIDATION HELPERS
# =====================================================

def is_valid_tool(tool_name: str) -> bool:
    return tool_name in TOOL_SCHEMAS


def get_schema(tool_name: str) -> Dict[str, Any] | None:
    return TOOL_SCHEMAS.get(tool_name)


def get_required_args(tool_name: str) -> List[str] | None:
    schema = TOOL_SCHEMAS.get(tool_name)
    if not schema:
        return None
    return schema.get("required", [])


def get_allowed_args(tool_name: str) -> List[str] | None:
    schema = TOOL_SCHEMAS.get(tool_name)
    if not schema:
        return None
    return list(schema.get("args", {}).keys())


# =====================================================
# STRICT VALIDATION (CORE GUARANTEE)
# =====================================================

def validate_tool_call(tool_name: str, args: dict) -> bool:

    if tool_name not in TOOL_SCHEMAS:
        raise ValueError(f"Unknown tool: {tool_name}")

    schema = TOOL_SCHEMAS[tool_name]
    required = schema.get("required", [])
    allowed = set(schema.get("args", {}).keys())

    if not isinstance(args, dict):
        raise ValueError("Args must be a dict")

    # Required args check
    for key in required:
        if key not in args:
            raise ValueError(f"Missing required argument: {key}")

    # Reject unknown args (strict mode)
    for key in args:
        if key not in allowed:
            raise ValueError(f"Unexpected argument: {key}")

    return True


# =====================================================
# PROMPT GENERATION (LLM CONTRACT ENFORCER)
# =====================================================

def get_tool_spec_for_prompt() -> str:

    lines = []

    for tool, spec in TOOL_SCHEMAS.items():

        lines.append(f"{tool}:")

        args = spec.get("args", {})
        required = set(spec.get("required", []))

        if not args:
            lines.append("  args: NONE")
        else:
            lines.append("  args:")

            for arg, arg_type in args.items():
                req = "required" if arg in required else "optional"
                lines.append(f"    - {arg} ({arg_type}, {req})")

        lines.append("")

    return "\n".join(lines)
