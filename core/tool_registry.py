# core/tool_registry.py
#
# Schema-enforced tool registry aligned with core/tool_schemas.py

from __future__ import annotations

from typing import Any, Callable, Dict, List, Type

from core.tool_schemas import (
    TOOL_REGISTRY,
    TOOL_SCHEMAS,
    get_tool,
    validate_tool_call,
)


class ToolDefinition:
    def __init__(
        self,
        name: str,
        func: Callable[..., Any],
        input_schema: Dict[str, Type[Any]],
        description: str = "",
        risk: str = "low",
        required_capabilities: List[str] | None = None,
    ):
        self.name = name
        self.func = func
        self.input_schema = input_schema
        self.description = description
        self.risk = risk
        self.required_capabilities = required_capabilities or []


class ToolRegistry:
    """Deterministic tool registry; schemas come from core.tool_schemas."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        func: Callable[..., Any],
        input_schema: Dict[str, Type[Any]] | None = None,
        description: str = "",
        risk: str = "low",
        required_capabilities: List[str] | None = None,
    ) -> None:
        if name in self._tools:
            raise ValueError(f"[ToolRegistry] Tool already registered: {name}")

        schema = input_schema if input_schema is not None else get_tool(name)

        if schema != get_tool(name) and name in TOOL_SCHEMAS:
            raise ValueError(
                f"[ToolRegistry] Schema drift for '{name}': "
                "must match core.tool_schemas.TOOL_SCHEMAS"
            )

        caps = required_capabilities
        if caps is None:
            from core.tool_contracts import has_contract, get_contract
            if has_contract(name):
                caps = list(get_contract(name).required_capabilities)

        self._tools[name] = ToolDefinition(
            name=name,
            func=func,
            input_schema=schema,
            description=description,
            risk=risk,
            required_capabilities=caps or [],
        )

    def has(self, name: str) -> bool:
        return name in self._tools

    def get(self, name: str) -> Callable[..., Any]:
        if name not in self._tools:
            raise ValueError(f"[ToolRegistry] Unknown tool: {name}")
        return self._tools[name].func

    def get_required_capabilities(self, name: str) -> List[str]:
        if name not in self._tools:
            raise ValueError(f"[ToolRegistry] Unknown tool: {name}")
        return list(self._tools[name].required_capabilities)

    def get_metadata(self, name: str) -> Dict[str, Any]:
        if name not in self._tools:
            raise ValueError(f"[ToolRegistry] Unknown tool: {name}")
        tool = self._tools[name]
        return {
            "name": tool.name,
            "description": tool.description,
            "risk": tool.risk,
            "schema": tool.input_schema,
        }

    def validate_args(self, name: str, args: Dict[str, Any]) -> None:
        result = validate_tool_call(name, args)
        if result["status"] != "success":
            raise ValueError(result.get("reason", "validation failed"))

    def run(self, name: str, args: Dict[str, Any]) -> Any:
        self.validate_args(name, args)
        tool = self.get(name)
        try:
            return tool(**args)
        except Exception as e:
            raise RuntimeError(
                f"[ToolRegistry] Tool execution failed: {name} -> {e}"
            ) from e
