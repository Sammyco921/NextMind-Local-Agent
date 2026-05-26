from tools.tool_registry import ToolRegistry
from tools.file_tools import write_file, read_file, list_dir


def load_tools(registry: ToolRegistry):

    registry.register(
        name="write_file",
        func=write_file,
        description="Write a file"
    )

    registry.register(
        name="read_file",
        func=read_file,
        description="Read a file"
    )

    registry.register(
        name="list_dir",
        func=list_dir,
        description="List directory contents"
    )

    return registry