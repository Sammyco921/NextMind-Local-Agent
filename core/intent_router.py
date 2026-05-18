class IntentRouter:
    """
    Simple deterministic intent classifier for early v0.5 system.
    No LLM dependency — purely rule-based routing.
    """

    def route(self, goal: str) -> str:

        if not goal:
            return "unknown"

        g = goal.lower()

        # -----------------------------
        # FILE / DIRECTORY INTENTS
        # -----------------------------
        if any(k in g for k in [
            "directory", "folder", "list", "summary", "report", "current"
        ]):
            return "dir_summary"

        # -----------------------------
        # FILE CREATION INTENTS
        # -----------------------------
        if any(k in g for k in [
            "create", "write", "make", "hello.txt", "notes", "file"
        ]):
            return "file_create"

        # -----------------------------
        # DEFAULT FALLBACK
        # -----------------------------
        return "dir_summary"