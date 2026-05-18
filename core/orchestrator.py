class Orchestrator:

    def __init__(
        self,
        planner,
        executor,
        state_model,
        logger,
        max_steps=10,
        max_failures=3
    ):
        self.planner = planner
        self.executor = executor
        self.state_model = state_model
        self.logger = logger

        self.max_steps = max_steps
        self.max_failures = max_failures

    # ====================================================
    # MAIN LOOP
    # ====================================================

    def run(self, goal: str):

        state = self.state_model.create(goal)

        failure_count = 0
        last_signature = None
        repeat_count = 0

        self.logger.info("Task started", {"goal": goal})

        try:

            while len(state["history"]) < self.max_steps:

                # ----------------------------------------
                # PLAN
                # ----------------------------------------
                try:
                    plan = self.planner.create_plan(goal, state)
                except Exception as e:
                    self.logger.error("Planner crash", {"error": str(e)})
                    return self._fatal(state, f"Planner failure: {e}")

                if not isinstance(plan, dict) or "steps" not in plan:
                    self.logger.error("Invalid planner output", plan)
                    return self._fatal(state, "Planner missing steps")

                steps = plan["steps"]

                if not steps:
                    return self._fatal(state, "Planner returned empty steps")

                step = steps[0]

                step = {
                    "id": step.get("id", len(state["history"])),
                    "tool": step.get("tool"),
                    "args": step.get("args", {})
                }

                # ----------------------------------------
                # LOOP DETECTION
                # ----------------------------------------
                signature = (step["tool"], str(step["args"]))

                if signature == last_signature:
                    repeat_count += 1
                else:
                    repeat_count = 0

                last_signature = signature

                if repeat_count >= 2:
                    self.logger.warning("Repeated step detected", step)
                    return self._fail(state, "Repeated identical steps detected", {"step": step})

                # ----------------------------------------
                # EXECUTION
                # ----------------------------------------
                self.logger.log_step(step)

                result = self.executor.run(step)

                self.logger.log_result(result)

                # ----------------------------------------
                # STORE HISTORY
                # ----------------------------------------
                state["history"].append({
                    "step": step,
                    "result": result
                })

                state["steps_executed"] = len(state["history"])

                # ----------------------------------------
                # FAILURE HANDLING
                # ----------------------------------------
                status = result.get("status")

                if status == "fatal_error":
                    self.logger.critical("Fatal execution error", result)
                    return self._fatal(state, result.get("error"))

                if status == "fail":
                    failure_count += 1
                    self.logger.warning("Tool failure", result)

                    if failure_count >= self.max_failures:
                        return self._fail(state, "Too many execution failures", result)

                    continue

                # success resets failure counter
                failure_count = 0

                # ----------------------------------------
                # SUCCESS CHECK
                # ----------------------------------------
                if self._goal_complete(goal, state):
                    self.logger.info("Goal completed", {"steps": state["steps_executed"]})

                    return {
                        "status": "success",
                        "goal": goal,
                        "steps_executed": state["steps_executed"],
                        "history": state["history"]
                    }

            # --------------------------------------------
            # MAX STEPS HIT
            # --------------------------------------------
            self.logger.warning("Max steps exceeded", state)

            return self._fail(state, "Max steps exceeded")

        except Exception as e:
            self.logger.critical("Orchestrator crash", {"error": str(e)})
            return self._fatal(state, str(e))

    # ====================================================
    # GOAL CHECK
    # ====================================================

    def _goal_complete(self, goal, state):

        if not state["history"]:
            return False

        last = state["history"][-1]["result"]

        if last.get("status") != "success":
            return False

        output = last.get("output")

        if output is None:
            return False

        goal_lower = goal.lower()

        if "read" in goal_lower:
            return isinstance(output, dict) and "content" in output

        if "write" in goal_lower or "create" in goal_lower:
            return True

        if "list" in goal_lower:
            return isinstance(output, dict) and "items" in output

        return False

    # ====================================================
    # FAILURE HELPERS
    # ====================================================

    def _fail(self, state, reason, details=None):

        self.logger.warning("Task failed", {"reason": reason, "details": details})

        return {
            "status": "fail",
            "goal": state["goal"],
            "reason": reason,
            "details": details,
            "steps_executed": len(state["history"]),
            "history": state["history"]
        }

    def _fatal(self, state, error):

        self.logger.critical("Task fatal error", {"error": error})

        return {
            "status": "fatal_error",
            "error": error,
            "goal": state.get("goal"),
            "steps_executed": len(state.get("history", [])),
            "history": state.get("history", [])
        }
