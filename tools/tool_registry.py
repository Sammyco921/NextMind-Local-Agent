from typing import Callable, Dict, Any


class ToolRegistry:
    """
    v0.9 Deterministic Tool Registry

    Responsibilities:
    - Store tool functions
    - Provide schemas for validation
    - Provide safe lookup interface
    """

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Dict[str, str]] = {}

    # =====================================================
    # REGISTER TOOL
    # =====================================================

    def register(
        self,
        name: str,
        func: Callable,
        schema: Dict[str, str]
    ) -> None:

        self._tools[name] = func
        self._schemas[name] = schema

    # =====================================================
    # LOOKUP TOOL
    # =====================================================

    def get(self, name: str):
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    # =====================================================
    # SCHEMA ACCESS
    # =====================================================

    def get_schema(self, name: str) -> Dict[str, str]:
        return self._schemas.get(name)

    # =====================================================
    # DEBUG HELPERS
    # =====================================================

    def list_tools(self):
        return list(self._tools.keys())


# =========================================================
# BUILD REGISTRY (CRITICAL FIX)
# =========================================================

def build_registry() -> ToolRegistry:
    """
    Single source of truth for tool availability.
    """

    registry = ToolRegistry()

    # -----------------------------------------------------
    # FILE SYSTEM TOOLS
    # -----------------------------------------------------

    def write_file(filename: str, content: str):
        with open(filename, "w") as f:
            f.write(content)
        return {"file": filename, "status": "written"}

    def read_file(filename: str):
        with open(filename, "r") as f:
            data = f.read()
        return {"file": filename, "content": data, "status": "read"}

    def list_dir():
        import os
        return {"path": ".", "items": os.listdir(".")}

    # -----------------------------------------------------
    # REGISTER ALL TOOLS
    # -----------------------------------------------------

    registry.register(
        "write_file",
        write_file,
        schema={
            "filename": "string",
            "content": "string"
        }
    )

    registry.register(
        "read_file",
        read_file,
        schema={
            "filename": "string"
        }
    )

    registry.register(
        "list_dir",
        list_dir,
        schema={}
    )

    return registry