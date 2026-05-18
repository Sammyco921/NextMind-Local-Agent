from core.llm import LLM
from core.planner import Planner
from core.executor import Executor
from core.critic import Critic
from core.orchestrator import Orchestrator
from core.logger import Logger

from state.state_model import StateModel

from tools.tool_registry import ToolRegistry
from tools.tool_schemas import TOOL_SCHEMAS

from tools.file_tools import write_file, read_file, list_dir


# ====================================================
# SYSTEM BUILDER
# ====================================================

def build_system():

    # ----------------------------------------
    # TOOL REGISTRY
    # ----------------------------------------
    registry = ToolRegistry()

    registry.register("write_file", write_file)
    registry.register("read_file", read_file)
    registry.register("list_dir", list_dir)

    # ----------------------------------------
    # CORE COMPONENTS
    # ----------------------------------------
    llm = LLM()

    planner = Planner(
        llm=llm,
        tool_schemas=TOOL_SCHEMAS
    )

    critic = Critic(
        valid_tools=list(TOOL_SCHEMAS.keys())
    )

    executor = Executor(
        registry=registry
    )

    state_model = StateModel()

    logger = Logger()

    # ----------------------------------------
    # ORCHESTRATOR (MAIN SYSTEM LOOP)
    # ----------------------------------------
    system = Orchestrator(
        planner=planner,
        executor=executor,
        state_model=state_model,
        logger=logger,
        critic=critic,
        max_steps=10,
        max_failures=3
    )

    return system


# ====================================================
# CLI LOOP
# ====================================================

def main():

    system = build_system()

    print("\n=== NextMind v0.4 ===\n")

    while True:

        try:
            goal = input("Enter goal (or 'exit'): ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if not goal:
            continue

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
