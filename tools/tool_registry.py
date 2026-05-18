class ToolRegistry:

    def __init__(self):
        self._tools = {}

    # ====================================================
    # REGISTER TOOL
    # ====================================================

    def register(self, name: str, func, description: str = "", schema: dict = None):

        if not isinstance(name, str):
            raise TypeError("Tool name must be a string")

        if not callable(func):
            raise TypeError("Tool function must be callable")

        name = self._normalize(name)

        self._tools[name] = {
            "name": name,
            "func": func,
            "description": description,
            "schema": schema or {}
        }

    # ====================================================
    # GET TOOL
    # ====================================================

    def get(self, name: str):

        name = self._normalize(name)

        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")

        return self._tools[name]

    # ====================================================
    # CALL TOOL (SAFE EXECUTION INTERFACE)
    # ====================================================

    def call(self, name: str, args: dict):

        if not isinstance(args, dict):
            raise TypeError("Tool args must be dict")

        tool = self.get(name)

        func = tool["func"]

        return func(**args)

    # ====================================================
    # LIST TOOLS
    # ====================================================

    def list_tools(self):

        return list(self._tools.values())

    # ====================================================
    # TOOL NAME NORMALIZATION
    # ====================================================

    def _normalize(self, name: str):

        return str(name).strip().lower()
