# tools/tool_registry.py
#
# NextMind v0.8 — Tool Registry
#
# Role:
#   Central mapping of tool names → callable functions
#
# Contract:
#   build_registry() is the ONLY public entry point


from tools.fs_tools import (
    list_dir,
    write_file,
    read_file
)


class ToolRegistry:

    def __init__(self):
        self._tools = {
            "list_dir": list_dir,
            "write_file": write_file,
            "read_file": read_file,
        }

    def has(self, name: str) -> bool:
        return name in self._tools

    def get(self, name: str):
        return self._tools.get(name)

    # optional compatibility (you hit earlier issues around this)
    def get_metadata(self, name: str):
        if name not in self._tools:
            return None
        return {
            "name": name,
            "available": True
        }


def build_registry():
    return ToolRegistry()