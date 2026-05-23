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
# TOOL REGISTRY (v1.1 STRICT MODE)
# =====================================================

class ToolRegistry:
    """
    Deterministic, schema-enforced tool registry.

    v1.1 guarantees:
    - strict input validation (no unknown args allowed)
    - strict required arg enforcement
    - deterministic tool resolution
    - clear execution error semantics
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    # =====================================================
    # REGISTER TOOL
    # =====================================================

    def register(
        self,
        name: str,
        func: Callable,
        input_schema: Dict[str, Type],
        description: str = "",
        risk: str = "low",
    ):

        if name in self._tools:
            raise ValueError(f"[ToolRegistry] Tool already registered: {name}")

        self._tools[name] = ToolDefinition(
            name=name,
            func=func,
            input_schema=input_schema,
            description=description,
            risk=risk,
        )

    # =====================================================
    # LOOKUP
    # =====================================================

    def has(self, name: str) -> bool:
        return name in self._tools

    def get(self, name: str) -> Callable:
        if name not in self._tools:
            raise ValueError(f"[ToolRegistry] Unknown tool: {name}")
        return self._tools[name].func

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

    # =====================================================
    # STRICT VALIDATION (CORE OF V1.1)
    # =====================================================

    def validate_args(self, name: str, args: Dict[str, Any]) -> None:

        if name not in self._tools:
            raise ValueError(f"[ToolRegistry] Unknown tool: {name}")

        schema = self._tools[name].input_schema

        # -------------------------------------------------
        # 1. missing required keys
        # -------------------------------------------------

        for key in schema:
            if key not in args:
                raise ValueError(
                    f"[ToolRegistry] Missing required arg '{key}' for tool '{name}'"
                )

        # -------------------------------------------------
        # 2. unknown keys (STRICT MODE)
        # -------------------------------------------------

        for key in args:
            if key not in schema:
                raise ValueError(
                    f"[ToolRegistry] Unexpected arg '{key}' for tool '{name}'"
                )

        # -------------------------------------------------
        # 3. type validation
        # -------------------------------------------------

        for key, expected_type in schema.items():
            value = args[key]

            if not isinstance(value, expected_type):
                raise TypeError(
                    f"[ToolRegistry] Tool '{name}' arg '{key}' expected "
                    f"{expected_type.__name__}, got {type(value).__name__}"
                )

    # =====================================================
    # SAFE EXECUTION ENTRYPOINT
    # =====================================================

    def run(self, name: str, args: Dict[str, Any]) -> Any:

        self.validate_args(name, args)

        tool = self.get(name)

        try:
            return tool(**args)

        except Exception as e:
            # normalize all tool failures into predictable shape
            raise RuntimeError(
                f"[ToolRegistry] Tool execution failed: {name} -> {str(e)}"
            )