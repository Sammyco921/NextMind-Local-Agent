from tools.file_tools import write_file, read_file, list_dir


"""
Tool Registry for NextMind

This is the single source of truth for all tools
available to the Executor and Planner.

Rules:
- Every tool must be explicitly registered here
- No dynamic execution allowed
- No hidden capabilities
"""


TOOL_REGISTRY = {
    # ========================================================
    # FILE SYSTEM TOOLS
    # ========================================================

    "write_file": write_file,
    "read_file": read_file,
    "list_dir": list_dir,
}


def get_tool(name: str):
    """
    Safe tool lookup.

    Args:
        name (str): Tool name

    Returns:
        callable: Tool function

    Raises:
        KeyError: If tool does not exist
    """

    if name not in TOOL_REGISTRY:
        raise KeyError(f"Tool not found: {name}")

    return TOOL_REGISTRY[name]


def list_tools() -> list:
    """
    Return list of available tool names.
    """

    return list(TOOL_REGISTRY.keys())
