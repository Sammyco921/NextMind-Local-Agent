class Orchestrator:

    def __init__(self, planner, executor, state_model, logger, max_steps=10, max_failures=3):

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

        steps = 0
        failures = 0

        while steps < self.max_steps:

            # ------------------------------------------------
            # 1. PLAN
            # ------------------------------------------------
            plan = self.planner.create_plan(goal, state)
            steps_list = plan.get("steps", [])

            if not steps_list:
                break

            step = steps_list[0]

            # ------------------------------------------------
            # 2. EXECUTE
            # ------------------------------------------------
            result = self.executor.run(step)

            # ------------------------------------------------
            # 3. UPDATE STATE
            # ------------------------------------------------
            state = self.state_model.update(state, step, result)

            # ------------------------------------------------
            # 4. FAILURE HANDLING
            # ------------------------------------------------
            if result.get("status") != "success":
                failures += 1
                if failures >= self.max_failures:
                    break
                steps += 1
                continue

            failures = 0

            # ------------------------------------------------
            # 5. STOP CONDITION (IMPORTANT FIX)
            # ------------------------------------------------
            if self._is_task_complete(goal, state):
                break

            steps += 1

        return state

    # ====================================================
    # COMPLETION DETECTION
    # ====================================================

    def _is_task_complete(self, goal: str, state: dict):

        history = state.get("history", [])

        if not history:
            return False

        last = history[-1]

        result = last.get("result", {})
        output = result.get("output", {})

        # ------------------------------------------------
        # FILE CREATION COMPLETION RULE
        # ------------------------------------------------
        if isinstance(output, dict):

            # Must have written report file successfully
            if output.get("file") == "report.txt":
                return True

        # ------------------------------------------------
        # FALLBACK: if planner explicitly used write_file
        # ------------------------------------------------
        last_step = last.get("step", {})
        if last_step.get("tool") == "write_file":
            if "report.txt" in str(last_step.get("args", {}).get("filename", "")):
                return True

        return False