from core.orchestrator import Orchestrator


def print_banner():
    print("\n" + "=" * 60)
    print("           NEXTMIND - LOCAL AGENT SYSTEM")
    print("=" * 60 + "\n")


def main():
    print_banner()

    orchestrator = Orchestrator()

    while True:
        try:
            goal = input("\nEnter goal (or 'exit'): ").strip()

            if goal.lower() in ["exit", "quit"]:
                print("\nShutting down NextMind.")
                break

            if not goal:
                print("Please enter a valid goal.")
                continue

            print("\n--- Running Task ---\n")

            result = orchestrator.run(goal)

            print("\n--- FINAL RESULT ---\n")
            print(result)

            print("\n" + "-" * 60 + "\n")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Exiting NextMind.")
            break

        except Exception as e:
            print(f"\n[ERROR] {str(e)}")


if __name__ == "__main__":
    main()
