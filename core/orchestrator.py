class Orchestrator:

    def __init__(
        self,
        planner,
        executor,
        critic,
        state_model,
        max_steps=10,
        max_failures=3
    ):
        self.planner = planner
        self.executor = executor
        self.critic = critic
        self.state_model = state_model

        self.max_steps = max_steps
        self.max_failures = max_failures

    # ====================================================
    # MAIN LOOP
    # ====================================================

    def run(self, goal: str):

        state = self.state_model.create(goal)

        failure_count = 0
        last_signature = None
        repeated_count = 0

        try:

            while len(state["history"]) < self.max_steps:

                # ----------------------------------------
                # PLAN
                # ----------------------------------------
                try:
                    plan = self.planner.create_plan(goal, state)

                except Exception as e:
                    return self._fatal(
                        state,
                        f"Planner failure: {e}"
                    )

                # ----------------------------------------
                # NORMALIZE PLAN
                # ----------------------------------------
                if isinstance(plan, list):
                    plan = {"steps": plan}

                if not isinstance(plan, dict):
                    return self._fatal(
                        state,
                        "Planner output must be dict"
                    )

                if "steps" not in plan:
                    return self._fatal(
                        state,
                        "Planner missing 'steps'"
                    )

                steps = plan["steps"]

                if not isinstance(steps, list):
                    return self._fatal(
                        state,
                        "'steps' must be a list"
                    )

                if len(steps) == 0:
                    return self._fatal(
                        state,
                        "Planner returned empty steps"
                    )

                # ----------------------------------------
                # GET FIRST STEP
                # ----------------------------------------
                step = steps[0]

                if not isinstance(step, dict):
                    return self._fatal(
                        state,
                        "Step must be dict"
                    )

                # ----------------------------------------
                # NORMALIZE STEP
                # ----------------------------------------
                step = {
                    "id": step.get(
                        "id",
                        len(state["history"])
                    ),
                    "tool": step.get("tool"),
                    "args": step.get("args", {})
                }

                # ----------------------------------------
                # LOOP DETECTION
                # ----------------------------------------
                signature = (
                    step["tool"],
                    str(step["args"])
                )

                if signature == last_signature:
                    repeated_count += 1
                else:
                    repeated_count = 0

                last_signature = signature

                if repeated_count >= 2:

                    return self._fail(
                        state,
                        "Repeated identical steps detected",
                        {"step": step}
                    )

                # ----------------------------------------
                # SHOW STEP
                # ----------------------------------------
                print("\n[Planner Step]")
                print(step)

                # ----------------------------------------
                # EXECUTION
                # ----------------------------------------
                try:
                    result = self.executor.run(step)

                except Exception as e:
                    return self._fatal(
                        state,
                        f"Executor crash: {e}"
                    )

                print("\n[Execution Result]")
                print(result)

                # ----------------------------------------
                # CRITIC VALIDATION
                # ----------------------------------------
                try:
                    critique = self.critic.evaluate_step(
                        step,
                        result
                    )

                except Exception as e:
                    return self._fatal(
                        state,
                        f"Critic crash: {e}"
                    )

                if critique.get("status") == "fail":

                    result = {
                        "status": "fail",
                        "error": critique.get("reason"),
                        "fix": critique.get(
                            "fix_suggestion"
                        ),
                        "step": step
                    }

                    print("\n[Critic Result]")
                    print(result)

                # ----------------------------------------
                # STORE HISTORY
                # ----------------------------------------
                state["history"].append({
                    "step": step,
                    "result": result
                })

                state["steps_executed"] = len(
                    state["history"]
                )

                # ----------------------------------------
                # FAILURE HANDLING
                # ----------------------------------------
                if (
                    not isinstance(result, dict)
                    or result.get("status") != "success"
                ):

                    failure_count += 1

                    if failure_count >= self.max_failures:

                        return self._fail(
                            state,
                            "Too many execution failures",
                            result
                        )

                    continue

                # ----------------------------------------
                # RESET FAILURES
                # ----------------------------------------
                failure_count = 0

                # ----------------------------------------
                # SUCCESS CHECK
                # ----------------------------------------
                if self._goal_complete(goal, state):

                    return {
                        "status": "success",
                        "goal": goal,
                        "steps_executed": state[
                            "steps_executed"
                        ],
                        "history": state["history"]
                    }

            # --------------------------------------------
            # MAX STEPS EXIT
            # --------------------------------------------
            return self._fail(
                state,
                "Max steps exceeded"
            )

        except Exception as e:

            return self._fatal(
                state,
                str(e)
            )

    # ====================================================
    # GOAL CHECK
    # ====================================================

    def _goal_complete(self, goal, state):

        if not state["history"]:
            return False

        last = state["history"][-1]["result"]

        if not isinstance(last, dict):
            return False

        if last.get("status") != "success":
            return False

        output = last.get("output")

        if output is None:
            return False

        goal_lower = goal.lower()

        if "read" in goal_lower:
            return (
                isinstance(output, dict)
                and output.get("content") is not None
            )

        if (
            "write" in goal_lower
            or "create" in goal_lower
        ):
            return True

        if "list" in goal_lower:
            return (
                isinstance(output, dict)
                and "items" in output
            )

        return False

    # ====================================================
    # FAILURE HELPERS
    # ====================================================

    def _fail(self, state, reason, details=None):

        return {
            "status": "fail",
            "goal": state["goal"],
            "reason": reason,
            "details": details,
            "steps_executed": len(
                state["history"]
            ),
            "history": state["history"]
        }

    def _fatal(self, state, error):

        return {
            "status": "fatal_error",
            "error": error,
            "goal": state.get("goal"),
            "steps_executed": len(
                state.get("history", [])
            ),
            "history": state.get("history", [])
        }
