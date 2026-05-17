from core.planner import Planner
from core.executor import Executor
from core.critic import Critic

from memory.memory_manager import MemoryManager

from config.config import AGENT_CONFIG


class Orchestrator:
    """
    Central control loop for NextMind.

    Responsibilities:
    - Receive user goals
    - Generate plans
    - Execute steps
    - Evaluate results
    - Handle retries/replanning
    - Store memory
    """

    def __init__(self):

        self.planner = Planner()
        self.executor = Executor()
        self.critic = Critic()
        self.memory = MemoryManager()

    # ========================================================
    # MAIN TASK LOOP
    # ========================================================

    def run(self, goal: str) -> dict:
        """
        Execute a full task lifecycle.

        Args:
            goal (str):
                User objective.

        Returns:
            dict:
                Final task result.
        """

        print(f"\n[NextMind] Goal Received:")
        print(f"→ {goal}\n")

        replan_count = 0

        # ----------------------------------------------------
        # Initial planning
        # ----------------------------------------------------

        plan = self.planner.create_plan(goal)

        if "steps" not in plan:
            return self._fail_task(
                "Planner failed to generate valid steps."
            )

        # ----------------------------------------------------
        # Main execution loop
        # ----------------------------------------------------

        while replan_count <= AGENT_CONFIG.MAX_REPLANS_PER_TASK:

            all_steps_passed = True

            for step in plan["steps"]:

                print(f"\n[Planner Step]")
                print(step)

                retry_count = 0

                # --------------------------------------------
                # Retry loop for a single step
                # --------------------------------------------

                while retry_count < AGENT_CONFIG.MAX_RETRIES_PER_STEP:

                    # ----------------------------------------
                    # Execute step
                    # ----------------------------------------

                    execution_result = self.executor.execute(step)

                    print(f"\n[Execution Result]")
                    print(execution_result)

                    # ----------------------------------------
                    # Critic evaluation
                    # ----------------------------------------

                    critic_result = self.critic.evaluate(
                        step=str(step),
                        execution_result=execution_result
                    )

                    print(f"\n[Critic Result]")
                    print(critic_result)

                    # ----------------------------------------
                    # Success path
                    # ----------------------------------------

                    if critic_result["status"] == "pass":

                        self.memory.store_step_result(
                            goal=goal,
                            step=step,
                            result=execution_result
                        )

                        break

                    # ----------------------------------------
                    # Failure path
                    # ----------------------------------------

                    retry_count += 1

                    print(
                        f"\n[Retry Attempt "
                        f"{retry_count}/"
                        f"{AGENT_CONFIG.MAX_RETRIES_PER_STEP}]"
                    )

                # --------------------------------------------
                # Step ultimately failed
                # --------------------------------------------

                if retry_count >= AGENT_CONFIG.MAX_RETRIES_PER_STEP:

                    print("\n[Step Failed] Replanning required.")

                    all_steps_passed = False
                    break

            # ------------------------------------------------
            # Entire task completed successfully
            # ------------------------------------------------

            if all_steps_passed:

                self.memory.store_task_summary(
                    goal=goal,
                    plan=plan
                )

                return {
                    "status": "success",
                    "goal": goal,
                    "plan": plan
                }

            # ------------------------------------------------
            # Replan logic
            # ------------------------------------------------

            replan_count += 1

            print(
                f"\n[Replanning "
                f"{replan_count}/"
                f"{AGENT_CONFIG.MAX_REPLANS_PER_TASK}]"
            )

            plan = self.planner.create_plan(
                goal=goal,
                previous_plan=plan
            )

        # ----------------------------------------------------
        # Task failed permanently
        # ----------------------------------------------------

        return self._fail_task(
            "Maximum replans exceeded."
        )

    # ========================================================
    # FAILURE HANDLER
    # ========================================================

    def _fail_task(self, reason: str) -> dict:
        """
        Standardized failure response.
        """

        return {
            "status": "fail",
            "reason": reason
        }
