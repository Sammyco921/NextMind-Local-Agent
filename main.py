# main.py
#
# NextMind v0.7 — Entry Point
#
# Minimal CLI runner for the deterministic pipeline system.
#
# Responsibilities:
#   - Accept user input
#   - Invoke Orchestrator
#   - Print structured result
#
# Non-responsibilities:
#   - No planning logic
#   - No execution logic
#   - No pipeline awareness


from core.orchestrator import Orchestrator
from core.planner import Planner
from tools.tool_registry import ToolRegistry


def build_registry() -> ToolRegistry:
    """
    Register all available tools here.
    In production, this can be replaced with auto-registration.
    """
    registry = ToolRegistry()

    # Example tools (replace with your real implementations)
    registry.register("write_file", write_file)
    registry.register("read_file", read_file)
    registry.register("list_dir", list_dir)

    return registry


# -----------------------------------------------------
# PLACEHOLDER TOOLS (replace with real implementations)
# -----------------------------------------------------

def write_file(filename: str, content: str):
    with open(filename, "w") as f:
        f.write(content)
    return {"file": filename, "bytes": len(content)}


def read_file(filename: str):
    with open(filename, "r") as f:
        return {"file": filename, "content": f.read()}


def list_dir(path: str = "."):
    import os
    return {
        "path": path,
        "items": os.listdir(path)
    }


# -----------------------------------------------------
# MAIN LOOP
# -----------------------------------------------------

def main():
    print("=== NextMind v0.7 (deterministic pipeline) ===\n")

    registry = build_registry()
    planner = Planner()
    orchestrator = Orchestrator(planner=planner, registry=registry)

    while True:
        try:
            goal = input("Enter goal (or 'exit'): ").strip()

            if goal.lower() == "exit":
                break

            result = orchestrator.run(goal)

            print("\n--- RESULT ---")
            print(result)
            print("\n" + "-" * 60 + "\n")

        except KeyboardInterrupt:
            print("\nExiting...")
            break

        except Exception as e:
            print(f"\nFatal error: {e}\n")


if __name__ == "__main__":
    main()
