class ToolRegistry:
    """
    Stable tool registry for NextMind v0.6
    - single source of truth for tool access
    - no hidden attributes
    - predictable API
    """

    def __init__(self):
        self._tools = {}

    # ----------------------------------------------------
    # REGISTER TOOL
    # ----------------------------------------------------
    def register(self, name: str, func):
        if not callable(func):
            raise ValueError(f"Tool '{name}' must be callable")

        self._tools[name] = func

    # ----------------------------------------------------
    # GET TOOL
    # ----------------------------------------------------
    def get(self, name: str):
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")

        return self._tools[name]

    # ----------------------------------------------------
    # CHECK EXISTENCE
    # ----------------------------------------------------
    def has(self, name: str) -> bool:
        return name in self._tools

    # ----------------------------------------------------
    # LIST TOOLS
    # ----------------------------------------------------
    def list(self):
        return list(self._tools.keys())

    # ----------------------------------------------------
    # BACKWARD COMPATIBILITY (IMPORTANT)
    # ----------------------------------------------------
    @property
    def tools(self):
        """
        Some of your older executor code expects `.tools`.
        This prevents AttributeError crashes.
        """
        return self._tools