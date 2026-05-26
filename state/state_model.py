class StateModel:

    def __init__(self):
        self.memory = {}

    # ====================================================
    # RESET STATE (MUST RETURN DICT)
    # ====================================================

    def reset(self):

        self.memory = {
            "goal": "",
            "history": [],
            "metadata": {}
        }

        return self.memory

    # ====================================================
    # OPTIONAL HELPERS (safe expansion)
    # ====================================================

    def update_goal(self, goal: str):
        self.memory["goal"] = goal

    def append_history(self, item: dict):
        self.memory["history"].append(item)

    def get_state(self):
        return self.memory