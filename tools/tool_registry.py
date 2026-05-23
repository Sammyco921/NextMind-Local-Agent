# core/tool_registry.py

from typing import Callable, Dict, Any, Type


# =====================================================
# TOOL DEFINITION
# =====================================================

class ToolDefinition:
    def __init__(
        self,
        name: str,
        func: Callable,
        input_schema: Dict[str, Type],
        description: str = "",
        risk: str = "low",
    ):
        self.name = name
        self.func = func
        self.input_schema = input_schema
        self.description = description
        self.risk = risk


# =====================================================
# TOOL REGISTRY (v1 LOCKED)
# =====================================================

class ToolRegistry:
    """
    Deterministic schema-enforced tool registry.

    v1 guarantees:
    - explicit schema validation
    - no unknown args allowed
    - no missing args allowed
    - safe tool lookup
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    # -------------------------------------------------
    # REGISTER TOOL
    # -------------------------------------------------

    def register(
        self,
        name: str,
        func: Callable,
        input_schema: Dict[str, Type],
        description: str = "",
        risk: str = "low",
    ):
        if name in self._tools:
            raise ValueError(f"[Registry] Tool already exists: {name}")

        self._tools[name] = ToolDefinition(
            name=name,
            func=func,
            input_schema=input_schema,
            description=description,
            risk=risk,
        )

    # -------------------------------------------------
    # LOOKUP
    # -------------------------------------------------

    def has(self, name: str) -> bool:
        return name in self._tools

    def get(self, name: str) -> Callable:
        return self._tools[name].func

    def get_metadata(self, name: str) -> Dict[str, Any]:
        tool = self._tools[name]
        return {
            "name": tool.name,
            "description": tool.description,
            "risk": tool.risk,
            "schema": tool.input_schema,
        }

    # -------------------------------------------------
    # VALIDATION (STRICT MODE)
    # -------------------------------------------------

    def validate_args(self, name: str, args: Dict[str, Any]) -> None:

        if name not in self._tools:
            raise ValueError(f"[Registry] Unknown tool: {name}")

        schema = self._tools[name].input_schema

        # 1. missing keys
        for key in schema:
            if key not in args:
                raise ValueError(
                    f"[Registry] Missing arg '{key}' for tool '{name}'"
                )

        # 2. unknown keys (this is what saved you from silent bugs)
        for key in args:
            if key not in schema:
                raise ValueError(
                    f"[Registry] Unexpected arg '{key}' for tool '{name}'"
                )

        # 3. type checking (lightweight, no pydantic yet)
        for key, expected_type in schema.items():
            if not isinstance(args[key], expected_type):
                raise TypeError(
                    f"[Registry] Tool '{name}' arg '{key}' expected "
                    f"{expected_type.__name__}, got {type(args[key]).__name__}"
                )

    # -------------------------------------------------
    # EXECUTION ENTRYPOINT
    # -------------------------------------------------

    def run(self, name: str, args: Dict[str, Any]) -> Any:

        if name not in self._tools:
            raise ValueError(f"[Registry] Unknown tool: {name}")

        self.validate_args(name, args)

        tool = self._tools[name].func
        return tool(**args)