import os
import sys
import argparse

from core.dag_planner import DAGPlanner
from core.dag_validator import DAGValidator
from core.dag_executor import DAGExecutor

from tools.tool_registry import ToolRegistry

# tools (explicit bootstrap layer)
from tools.write_file import write_file
from tools.read_file import read_file
from tools.list_dir import list_dir


# =====================================================
# PATH BOOTSTRAP
# =====================================================

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# =====================================================
# TOOL BOOTSTRAP (SINGLE SOURCE OF TRUTH)
# =====================================================

def bootstrap_tools(registry: ToolRegistry):

    registry.register(
        name="write_file",
        func=write_file,
        input_schema={
            "filename": str,
            "content": str
        },
        description="Write a file to disk"
    )

    registry.register(
        name="read_file",
        func=read_file,
        input_schema={
            "filename": str
        },
        description="Read a file from disk"
    )

    registry.register(
        name="list_dir",
        func=list_dir,
        input_schema={},
        description="List directory contents"
    )


# =====================================================
# DAG NORMALIZER
# =====================================================

def normalize_dag(dag):

    steps = []

    for node in getattr(dag, "nodes", []):

        steps.append({
            "_id": node.node_id,
            "tool": node.tool,
            "args": node.args or {},
            "depends_on": node.depends_on or []
        })

    return steps


# =====================================================
# PIPELINE RUNNER
# =====================================================

def run_pipeline(goal: str, debug: bool = False):

    # ---------------------------------------------
    # 1. CORE INITIALIZATION
    # ---------------------------------------------
    registry = ToolRegistry()
    bootstrap_tools(registry)

    planner = DAGPlanner()
    validator = DAGValidator(registry)
    executor = DAGExecutor(registry)

    # ---------------------------------------------
    # 2. PLANNING
    # ---------------------------------------------
    dag = planner.plan(goal)

    # ---------------------------------------------
    # 3. VALIDATION (HARD GATE)
    # ---------------------------------------------
    validation = validator.validate(dag)

    if validation["status"] != "valid":

        print("\n--- VALIDATION FAILED ---")

        for err in validation["errors"]:
            print(" -", err)

        return

    # ---------------------------------------------
    # 4. NORMALIZATION
    # ---------------------------------------------
    steps = normalize_dag(dag)

    # ---------------------------------------------
    # 5. EXECUTION
    # ---------------------------------------------
    result = executor.execute(dag, goal)

    # ---------------------------------------------
    # 6. OUTPUT
    # ---------------------------------------------
    if debug:
        print("\n=== DEBUG EXECUTION TRACE ===\n")

        for t in result.trace:
            print(f"[{t['status']}] {t['tool']} -> {t['id']}")
            if t["status"] != "success":
                print("   ERROR:", t["result"])

    else:
        print("\n--- RESULT ---")
        print(result.to_dict())


# =====================================================
# MAIN LOOP
# =====================================================

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    print("\n=== NextMind v1.1 ===\n")

    while True:

        goal = input("\nEnter goal (or 'exit'): ")

        if goal.strip().lower() == "exit":
            print("Exiting...")
            break

        print("\n--- PIPELINE START ---")
        run_pipeline(goal, debug=args.debug)


# =====================================================
# ENTRYPOINT
# =====================================================

if __name__ == "__main__":
    main()
