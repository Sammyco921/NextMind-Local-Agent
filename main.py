from core.executor import Executor
from core.orchestrator import Orchestrator
from core.planner import Planner
from core.intent_router import IntentRouter
from state.state_model import StateModel
from core.logger import Logger

from tools.tool_registry import ToolRegistry
from tools.tool_loader import load_tools


# ====================================================
# BUILD SYSTEM
# ====================================================

def build_system():

    # -----------------------------
    # TOOL REGISTRY + LOADER
    # -----------------------------

    registry = ToolRegistry()
    registry = load_tools(registry)

    # -----------------------------
    # CORE COMPONENTS
    # -----------------------------

    executor = Executor(registry)
    state_model = StateModel()
    logger = Logger()

    # -----------------------------
    # INTENT ROUTER (NEW REQUIRED DEPENDENCY)
    # -----------------------------

    intent_router = IntentRouter()

    # -----------------------------
    # PLANNER
    # -----------------------------

    planner = Planner(
        tool_schemas=registry.list_tools(),
        intent_router=intent_router
    )

    # -----------------------------
    # ORCHESTRATOR
    # -----------------------------

    system = Orchestrator(
        planner=planner,
        executor=executor,
        state_model=state_model,
        logger=logger,
        max_steps=10,
        max_failures=3
    )

    return system


# ====================================================
# MAIN LOOP
# ====================================================

def main():

    system = build_system()

    print("\n=== NextMind v0.5 ===\n")

    while True:

        goal = input("Enter goal (or 'exit'): ")

        if goal.strip().lower() == "exit":
            break

        print("\n--- Running task ---\n")

        result = system.run(goal)

        print("\n--- FINAL RESULT ---\n")
        print(result)
        print("\n" + "-" * 60 + "\n")


if __name__ == "__main__":
    main()