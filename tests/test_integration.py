from core.dag_planner import DAGPlanner
from core.dag_validator import DAGValidator
from core.executor import Executor
from tools.tool_registry import ToolRegistry
from tools.write_file import write_file
from tools.read_file import read_file
from tools.list_dir import list_dir


def setup_system():

    registry = ToolRegistry()

    registry.register("write_file", write_file, {
        "filename": str,
        "content": str
    })

    registry.register("read_file", read_file, {
        "filename": str
    })

    registry.register("list_dir", list_dir, {})

    return (
        DAGPlanner(),
        DAGValidator(registry),
        Executor(registry)
    )


def test_full_pipeline_smoke():

    planner, validator, executor = setup_system()

    goal = "create and read a file then list directory"

    dag = planner.plan(goal)
    validation = validator.validate(dag)

    assert validation["status"] == "valid"

    steps = [
        {
            "_id": 1,
            "tool": "list_dir",
            "args": {}
        }
    ]

    result = executor.execute(goal, steps)

    assert result.goal == goal