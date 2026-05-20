from typing import Dict, Any, List


# =====================================================
# TOOL SCHEMA REGISTRY (SOURCE OF TRUTH)
# =====================================================

TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {

    "write_file": {
        "args": {
            "filename": "str",
            "content": "str"
        },
        "required": ["filename", "content"]
    },

    "read_file": {
        "args": {
            "filename": "str"
        },
        "required": ["filename"]
    },

    "list_dir": {
        "args": {
            "path": "str"
        },
        "required": []
    }
}


# =====================================================
# VALID TOOL CHECK
# =====================================================

def is_valid_tool(tool_name: str) -> bool:
    return tool_name in TOOL_SCHEMAS


def get_schema(tool_name: str) -> Dict[str, Any]:
    return TOOL_SCHEMAS.get(tool_name, {})


# =====================================================
# CORE VALIDATOR (IMPORTANT)
# =====================================================

def validate_tool_call(tool_name: str, args: dict) -> dict:

    if tool_name not in TOOL_SCHEMAS:
        return {
            "status": "fail",
            "reason": f"Unknown tool: {tool_name}"
        }

    schema = TOOL_SCHEMAS[tool_name]
    required = schema.get("required", [])
    allowed = set(schema.get("args", {}).keys())

    if not isinstance(args, dict):
        return {
            "status": "fail",
            "reason": "Args must be a dictionary"
        }

    # ---------------------------------------------
    # REQUIRED ARG CHECK
    # ---------------------------------------------
    for key in required:
        if key not in args:
            return {
                "status": "fail",
                "reason": f"Missing required argument: {key}"
            }

    # ---------------------------------------------
    # UNKNOWN ARG CHECK
    # ---------------------------------------------
    for key in args:
        if key not in allowed:
            return {
                "status": "fail",
                "reason": f"Unexpected argument: {key}"
            }

    # ---------------------------------------------
    # EMPTY STRING GUARD (IMPORTANT FIX)
    # ---------------------------------------------
    for key, value in args.items():
        if isinstance(value, str) and value.strip() == "":
            return {
                "status": "fail",
                "reason": f"Argument '{key}' cannot be empty string"
            }

    return {
        "status": "success"
    }


# =====================================================
# TOOL LIST FOR PLANNER PROMPT
# =====================================================

def get_tool_spec_for_prompt() -> str:

    lines = []

    for tool, spec in TOOL_SCHEMAS.items():

        lines.append(f"{tool}:")

        args = spec.get("args", {})
        required = set(spec.get("required", []))

        for arg, arg_type in args.items():
            req = "required" if arg in required else "optional"
            lines.append(f"  - {arg} ({arg_type}, {req})")

        lines.append("")

    return "\n".join(lines)


# =====================================================
# SAFE TOOL WRAPPER (OPTIONAL BUT POWERFUL)
# =====================================================

def safe_call(tool_name: str, args: dict, registry):

    validation = validate_tool_call(tool_name, args)

    if validation["status"] == "fail":
        return {
            "status": "fail",
            "error": validation["reason"]
        }

    tool = registry.get(tool_name)
    func = tool["func"]

    try:
        output = func(**args)

        return {
            "status": "success",
            "output": output
        }

    except Exception as e:
        return {
            "status": "fatal_error",
            "error": str(e)
        }
