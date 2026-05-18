from core.llm import LLM
from core.planner import Planner
from core.executor import Executor
from core.critic import Critic
from core.orchestrator import Orchestrator
from tools.tool_registry import ToolRegistry
from tools.tool_schemas import TOOL_SCHEMAS
from state.state_model import StateModel

from tools.file_tools import write_file, read_file, list_dir


# ====================================================
# BUILD SYSTEM
# ====================================================

def build_system():

    # ----------------------------
    # REGISTRY
    # ----------------------------
    registry = ToolRegistry()

    registry.register("write_file", write_file)
    registry.register("read_file", read_file)
    registry.register("list_dir", list_dir)

    # ----------------------------
    # CORE COMPONENTS
    # ----------------------------
    llm = LLM()

    planner = Planner(
        llm=llm,
        tool_schemas=TOOL_SCHEMAS
    )

    critic = Critic(valid_tools=[
        "write_file",
        "read_file",
        "list_dir"
    ])

    executor = Executor(
        registry=registry,
        critic=critic
    )

    state_model = StateModel()

    # ----------------------------
    # ORCHESTRATOR
    # ----------------------------

    system = Orchestrator(
        planner=planner,
        executor=executor,
        critic=critic,
        state_model=state_model,
        max_steps=10,
        max_failures=3
    )

    return system


# ====================================================
# CLI LOOP
# ====================================================

def main():

    system = build_system()

    print("\n=== NextMind v0.3 ===\n")

    while True:

        goal = input("Enter goal (or 'exit'): ")

        if goal.strip().lower() == "exit":
            break

        print("\n--- Running task ---\n")

        result = system.run(goal)

        print("\n--- FINAL RESULT ---\n")
        print(result)
        print("\n" + "-" * 60 + "\n")


# ====================================================
# ENTRY POINT
# ====================================================

if __name__ == "__main__":
    main()
