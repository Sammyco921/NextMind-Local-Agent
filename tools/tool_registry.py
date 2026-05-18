class ToolRegistry:

    def __init__(self):
        self._tools = {}

    def register(self, name: str, func, description: str = "", schema: dict = None):
        if not isinstance(name, str):
            raise TypeError("Tool name must be a string")

        if not callable(func):
            raise TypeError("Tool function must be callable")

        self._tools[name] = {
            "name": name,
            "func": func,
            "description": description,
            "schema": schema or {}
        }

    def get(self, name: str):
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")

        return self._tools[name]

    def list_tools(self):
        return list(self._tools.values())