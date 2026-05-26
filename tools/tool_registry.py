# tools/tool_registry.py
#
# Compatibility re-export — canonical implementation is core.tool_registry.

from core.tool_registry import ToolDefinition, ToolRegistry
from core.tool_schemas import (
    TOOL_REGISTRY,
    TOOL_SCHEMAS,
    get_tool,
    validate_tool_call,
)

__all__ = [
    "ToolDefinition",
    "ToolRegistry",
    "TOOL_REGISTRY",
    "TOOL_SCHEMAS",
    "get_tool",
    "validate_tool_call",
]
