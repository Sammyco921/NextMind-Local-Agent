class ContextBuilder:
    """
    v0.5 Context Builder

    Purpose:
    - Merge goal + history + observation state
    - Produce a structured input for the planner
    - Prevent raw/ungrounded planning inputs
    """

    def __init__(self):
        pass

    # ====================================================
    # MAIN ENTRY
    # ====================================================

    def build(self, goal: str, state: dict, observation: dict):
        """
        Creates a planner-ready context object.
        """

        if not isinstance(state, dict):
            state = {}

        if not isinstance(observation, dict):
            observation = {}

        history = state.get("history", [])

        return {
            "goal": goal,

            # ----------------------------------------
            # CORE STATE
            # ----------------------------------------
            "step_count": len(history),
            "recent_steps": self._compact_history(history),

            # ----------------------------------------
            # GROUNDED ENVIRONMENT STATE
            # ----------------------------------------
            "files": observation.get("files", []),
            "facts": observation.get("recent_facts", []),
            "recent_outputs": observation.get("recent_outputs", []),

            # ----------------------------------------
            # EXECUTION SIGNALS
            # ----------------------------------------
            "last_result": self._last_result(history),
            "failure_signals": self._extract_failures(history),

            # ----------------------------------------
            # PLANNING HINTS (IMPORTANT)
            # ----------------------------------------
            "needs_observation": self._needs_observation_hint(observation, history)
        }

    # ====================================================
    # HISTORY COMPRESSION
    # ====================================================

    def _compact_history(self, history):
        """
        Reduce history to planner-relevant signal only.
        """

        compact = []

        for h in history[-5:]:
            step = h.get("step", {})
            result = h.get("result", {})

            compact.append({
                "tool": step.get("tool"),
                "args": step.get("args"),
                "status": result.get("status")
            })

        return compact

    # ====================================================
    # LAST RESULT EXTRACTION
    # ====================================================

    def _last_result(self, history):
        if not history:
            return None

        return history[-1].get("result")

    # ====================================================
    # FAILURE SIGNAL EXTRACTION
    # ====================================================

    def _extract_failures(self, history):
        failures = []

        for h in history[-5:]:
            result = h.get("result", {})
            if result.get("status") in ["fail", "fatal_error"]:
                failures.append({
                    "tool": h.get("step", {}).get("tool"),
                    "error": result.get("error")
                })

        return failures

    # ====================================================
    # OBSERVATION NEED DETECTION
    # ====================================================

    def _needs_observation_hint(self, observation, history):
        """
        Lightweight heuristic:
        forces planner to prefer list/read when state is uncertain.
        """

        if not observation:
            return True

        files = observation.get("files", [])

        # If no known files but file-related goal likely exists
        if len(files) == 0:
            return True

        # If last step failed repeatedly
        if len(history) >= 2:
            last = history[-1].get("result", {})
            prev = history[-2].get("result", {})

            if last.get("status") == "fail" and prev.get("status") == "fail":
                return True

        return False