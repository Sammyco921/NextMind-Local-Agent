from tools.tool_registry import build_registry
from core.planner import Planner
from core.orchestrator import Orchestrator
from core.validator import Validator
from tests.test_harness import TestHarness


# =========================================================
# CLI MODE
# =========================================================

def run_cli(orchestrator: Orchestrator):

    print("=== NextMind v0.9 (Deterministic Kernel) ===\n")

    while True:

        try:

            goal = input("Enter goal (or 'exit'): ").strip()

            if goal.lower() == "exit":
                print("Exiting...")
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


# =========================================================
# TEST MODE
# =========================================================

def run_tests(registry, planner, validator):

    print("=== Running v0.9 Test Harness ===\n")

    harness = TestHarness(
        registry=registry,
        planner=planner
    )

    summary = harness.run_default_suite()

    harness.print_summary(summary)


# =========================================================
# ENTRYPOINT
# =========================================================

def main():

    registry = build_registry()
    planner = Planner()
    validator = Validator(registry)
    orchestrator = Orchestrator(
        planner=planner,
        registry=registry,
        validator=validator
    )

    print("Select mode:")
    print("1. CLI")
    print("2. TEST SUITE\n")

    mode = input("Mode (1/2): ").strip()

    if mode == "1":
        run_cli(orchestrator)

    elif mode == "2":
        run_tests(registry, planner, validator)

    else:
        print("Invalid mode")


if __name__ == "__main__":
    main()