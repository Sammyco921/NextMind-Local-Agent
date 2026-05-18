from typing import Dict, Any, List


# =====================================================
# TOOL SCHEMA REGISTRY (STRICT CONTRACT LAYER)
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
        "required": ["filename", "content"],
        "forbidden_values": {
            "filename": [""],
            "content": [None]
        }
    },

    # -------------------------------------------------
    # READ FILE
    # -------------------------------------------------
    "read_file": {
        "args": {
            "filename": "str"
        },
        "required": ["filename"],
        "forbidden_values": {
            "filename": [""]
        }
    },

    # -------------------------------------------------
    # LIST DIRECTORY
    # -------------------------------------------------
    "list_dir": {
        "args": {
            "path": "str"
        },
        "required": [],
        "forbidden_values": {
            "path": [None]
        }
    }
}


# =====================================================
# BASIC HELPERS
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
# STRICT VALIDATION (CORE GUARANTEE LAYER)
# =====================================================

def validate_tool_call(tool_name: str, args: dict) -> bool:

    if tool_name not in TOOL_SCHEMAS:
        raise ValueError(f"Unknown tool: {tool_name}")

    schema = TOOL_SCHEMAS[tool_name]

    required = schema.get("required", [])
    allowed = set(schema.get("args", {}).keys())
    forbidden = schema.get("forbidden_values", {})

    if not isinstance(args, dict):
        raise ValueError("Args must be a dict")

    # -----------------------------
    # REQUIRED CHECK
    # -----------------------------
    for key in required:
        if key not in args:
            raise ValueError(f"Missing required argument: {key}")

    # -----------------------------
    # UNKNOWN ARG REJECTION
    # -----------------------------
    for key in args:
        if key not in allowed:
            raise ValueError(f"Unexpected argument: {key}")

    # -----------------------------
    # FORBIDDEN VALUE CHECK
    # -----------------------------
    for key, bad_values in forbidden.items():

        if key not in args:
            continue

        if args[key] in bad_values:
            raise ValueError(
                f"Invalid value for {key}: {args[key]}"
            )

    return True


# =====================================================
# PROMPT HELPER (FOR PLANNER)
# =====================================================

def get_tool_spec_for_prompt() -> str:

    lines = []

    for tool, spec in TOOL_SCHEMAS.items():

        lines.append(f"{tool}:")

        args = spec.get("args", {})
        required = set(spec.get("required", []))
        forbidden = spec.get("forbidden_values", {})

        if not args:
            lines.append("  args: NONE")
        else:
            lines.append("  args:")

            for arg, arg_type in args.items():
                req = "required" if arg in required else "optional"
                forbidden_hint = ""

                if arg in forbidden:
                    forbidden_hint = f" (forbidden: {forbidden[arg]})"

                lines.append(f"    - {arg} ({arg_type}, {req}){forbidden_hint}")

        lines.append("")

    return "\n".join(lines)
