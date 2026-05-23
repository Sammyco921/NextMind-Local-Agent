class MemoryManager:

    def __init__(self):
        self.memory = []

    # ====================================================
    # MAIN RECORD FUNCTION (FIXES YOUR CRASH)
    # ====================================================
    def record(self, state, step, result):

        entry = {
            "goal": state.get("goal"),
            "step": step,
            "result": result,
            "iteration": state.get("iteration", 0)
        }

        self.memory.append(entry)

    # ====================================================
    # SAFE READ ACCESS
    # ====================================================
    def get_all(self):
        return self.memory

    def get_last(self):
        if not self.memory:
            return None
        return self.memory[-1]

    # ====================================================
    # OPTIONAL: CONTEXT BUILDER (SAFE)
    # ====================================================
    def build_context(self, limit=5):

        return {
            "recent_steps": self.memory[-limit:] if self.memory else [],
            "total_records": len(self.memory)
        }

    # ====================================================
    # CLEAR MEMORY (DEBUG / RESET)
    # ====================================================
    def clear(self):
        self.memory = []