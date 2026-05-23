from core.executor import Executor
from tools.tool_registry import ToolRegistry
from tools.write_file import write_file
from tools.read_file import read_file


def setup_executor():

    registry = ToolRegistry()

    registry.register("write_file", write_file, {
        "filename": str,
        "content": str
    })

    registry.register("read_file", read_file, {
        "filename": str
    })

    return Executor(registry)


def test_executor_runs_single_step():

    executor = setup_executor()

    steps = [
        {
            "_id": 1,
            "tool": "write_file",
            "args": {
                "filename": "src/executor_test.txt",
                "content": "abc"
            }
        }
    ]

    result = executor.execute("test goal", steps)

    assert result.status == "success"
    assert result.steps_executed == 1
    assert len(result.trace) == 1