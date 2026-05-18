class StateModel:

    # ====================================================
    # CREATE INITIAL STATE
    # ====================================================

    def create(self, goal: str):

        if not isinstance(goal, str):
            raise TypeError("Goal must be a string")

        return {
            "goal": goal,
            "history": [],
            "step_index": 0,
            "status": "running"
        }

    # ====================================================
    # UPDATE STATE AFTER STEP
    # ====================================================

    def update(self, state: dict, step: dict, result: dict):

        if not isinstance(state, dict):
            raise TypeError("State must be dict")

        if "history" not in state:
            state["history"] = []

        state["history"].append({
            "step": step,
            "result": result
        })

        state["step_index"] = len(state["history"])

        return state

    # ====================================================
    # GETTERS (SAFE ACCESS LAYER)
    # ====================================================

    def get_history(self, state: dict):
        return state.get("history", [])

    def get_last_result(self, state: dict):

        history = state.get("history", [])

        if not history:
            return None

        return history[-1].get("result")

    def get_last_step(self, state: dict):

        history = state.get("history", [])

        if not history:
            return None

        return history[-1].get("step")
