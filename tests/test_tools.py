import pytest
from tools.tool_registry import ToolRegistry
from tools.write_file import write_file
from tools.read_file import read_file
from tools.list_dir import list_dir


def setup_registry():
    registry = ToolRegistry()

    registry.register("write_file", write_file, {
        "filename": str,
        "content": str
    })

    registry.register("read_file", read_file, {
        "filename": str
    })

    registry.register("list_dir", list_dir, {})

    return registry


def test_write_and_read_cycle():
    registry = setup_registry()

    registry.run("write_file", {
        "filename": "src/test_a.txt",
        "content": "hello world"
    })

    result = registry.run("read_file", {
        "filename": "src/test_a.txt"
    })

    assert result["content"] == "hello world"


def test_list_dir_runs():
    registry = setup_registry()

    result = registry.run("list_dir", {})

    assert "items" in result
    assert isinstance(result["items"], list)


def test_registry_rejects_unknown_tool():
    registry = setup_registry()

    with pytest.raises(ValueError):
        registry.run("fake_tool", {})