from core.planner import Planner
from core.executor import Executor
from core.orchestrator import Orchestrator

from tools.tool_registry import ToolRegistry
from tools.write_file import write_file
from tools.read_file import read_file
from tools.list_dir import list_dir


def build_system():

    # ====================================================
    # TOOL REGISTRY (single source of truth)
    # ====================================================
    registry = ToolRegistry()

    registry.register("write_file", write_file)
    registry.register("read_file", read_file)
    registry.register("list_dir", list_dir)

    # ====================================================
    # CORE COMPONENTS
    # ====================================================

    planner = Planner()

    executor = Executor(registry)

    orchestrator = Orchestrator(
        planner=planner,
        executor=executor
    )

    return orchestrator


def main():

    system = build_system()

    print("=== NextMind v0.6 (stable runtime) ===\n")

    while True:

        goal = input("Enter goal (or 'exit'): ")

        if goal.strip().lower() == "exit":
            break

        print("\n--- Running task ---\n")

        result = system.run(goal)

        print("\n--- FINAL RESULT ---\n")
        print(result)

        print("\n------------------------------------------------------------\n")


if __name__ == "__main__":
    main()