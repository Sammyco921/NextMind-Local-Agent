import os
import sys

# =====================================================
# BOOTSTRAP
# =====================================================

ROOT = os.path.dirname(os.path.abspath(__file__))

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# =====================================================
# IMPORTS
# =====================================================

from core.dag_planner import DAGPlanner
from core.dag_validator import DAGValidator
from core.executor import Executor
from tools.tool_registry import ToolRegistry

from tools.write_file import write_file
from tools.read_file import read_file
from tools.list_dir import list_dir


# =====================================================
# TOOL REGISTRATION
# =====================================================

def build_registry() -> ToolRegistry:

    registry = ToolRegistry()

    # -------------------------------------------------
    # WRITE FILE
    # -------------------------------------------------

    registry.register(
        name="write_file",
        func=write_file,
        input_schema={
            "filename": str,
            "content": str,
        },
        description="Write content to a file.",
        risk="low",
    )

    # -------------------------------------------------
    # READ FILE
    # -------------------------------------------------

    registry.register(
        name="read_file",
        func=read_file,
        input_schema={
            "filename": str,
        },
        description="Read file contents.",
        risk="low",
    )

    # -------------------------------------------------
    # LIST DIRECTORY
    # -------------------------------------------------

    registry.register(
        name="list_dir",
        func=list_dir,
        input_schema={},
        description="List files in working directory.",
        risk="low",
    )

    return registry


# =====================================================
# DAG NORMALIZER
# =====================================================

def normalize_dag(dag):

    steps = []

    for node in dag.nodes:

        steps.append({
            "_id": node.node_id,
            "tool": node.tool,
            "args": node.args or {},
            "depends_on": node.depends_on or [],
        })

    return steps


# =====================================================
# MAIN LOOP
# =====================================================

def main():

    print("\n=== NextMind v1 ===")

    # -------------------------------------------------
    # SYSTEM INIT
    # -------------------------------------------------

    registry = build_registry()

    planner = DAGPlanner()

    validator = DAGValidator(registry)

    executor = Executor(registry)

    # -------------------------------------------------
    # REPL LOOP
    # -------------------------------------------------

    while True:

        goal_input = input("\nEnter goal (or 'exit'): ").strip()

        if goal_input.lower() == "exit":
            print("Exiting...")
            break

        try:

            print("\n--- PIPELINE START ---")

            # =================================================
            # PLAN
            # =================================================

            dag = planner.plan(goal_input)

            # =================================================
            # VALIDATE
            # =================================================

            validation = validator.validate(dag)

            if validation["status"] != "valid":

                print("\n--- VALIDATION FAILED ---")

                for err in validation["errors"]:
                    print(f" - {err}")

                continue

            # =================================================
            # NORMALIZE
            # =================================================

            steps = normalize_dag(dag)

            # =================================================
            # EXECUTE
            # =================================================

            result = executor.execute(goal_input, steps)

            # =================================================
            # OUTPUT
            # =================================================

            print("\n--- RESULT ---")

            print(result.to_dict())

        except Exception as e:

            print("\n--- FATAL ERROR ---")

            print(type(e).__name__)
            print(str(e))


# =====================================================
# ENTRYPOINT
# =====================================================

if __name__ == "__main__":
    main()
