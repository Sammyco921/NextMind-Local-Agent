from core.memory_manager import MemoryManager


class StateModel:

    def __init__(self, memory: MemoryManager = None):

        self.memory = memory

    # ====================================================
    # CREATE INITIAL STATE
    # ====================================================

    def create(self, goal: str):

        return {
            "goal": goal,
            "history": [],
            "steps_executed": 0,
            "memory_context": self._get_memory_context()
        }

    # ====================================================
    # UPDATE STATE (OPTIONAL UTILITY)
    # ====================================================

    def update(self, state: dict, step: dict, result: dict):

        if "history" not in state:
            state["history"] = []

        state["history"].append({
            "step": step,
            "result": result
        })

        state["steps_executed"] = len(state["history"])

        return state

    # ====================================================
    # MEMORY INJECTION (CRITICAL FOR v0.5+)
    # ====================================================

    def _get_memory_context(self):

        if not self.memory:
            return {
                "recent_tasks": [],
                "recent_errors": [],
                "recent_events": []
            }

        return self.memory.build_context()

    # ====================================================
    # REFRESH MEMORY CONTEXT (OPTIONAL)
    # ====================================================

    def refresh_memory(self, state: dict):

        state["memory_context"] = self._get_memory_context()

        return state

    # ====================================================
    # STATE SANITY CHECK (DEBUG TOOL)
    # ====================================================

    def validate(self, state: dict):

        if not isinstance(state, dict):
            return False

        required_keys = ["goal", "history", "steps_executed"]

        for key in required_keys:
            if key not in state:
                return False

        if not isinstance(state["history"], list):
            return False

        return True
