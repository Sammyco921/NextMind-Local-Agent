class Planner:

    def __init__(self, tool_schemas, intent_router):
        self.tools = tool_schemas
        self.intent_router = intent_router

    # ====================================================
    # MAIN ENTRY
    # ====================================================

    def create_plan(self, goal: str, state: dict):

        history = state.get("history", [])
        intent = self.intent_router.route(goal)

        last_tool = history[-1]["step"]["tool"] if history else None

        # ====================================================
        # GUARD: EMPTY INPUT
        # ====================================================

        if not goal or not goal.strip():
            return {"done": True, "reason": "empty goal"}

        # ====================================================
        # GUARD: STOP IF RECENT TOOL LOOP DETECTED
        # ====================================================

        recent_tools = [h.get("step", {}).get("tool") for h in history[-3:]]

        if recent_tools.count("list_dir") >= 2:
            return {"done": True, "reason": "loop prevention"}

        # ====================================================
        # INTENT: DIRECTORY SUMMARY
        # ====================================================

        if intent == "dir_summary":

            if last_tool == "list_dir":
                return {"done": True, "reason": "already inspected directory"}

            return {
                "steps": [
                    {
                        "id": len(history),
                        "tool": "list_dir",
                        "args": {}
                    }
                ]
            }

        # ====================================================
        # INTENT: FILE CREATION
        # ====================================================

        if intent == "file_create":

            # Step 1: ensure directory context (ONLY ONCE)
            if not any(h["step"]["tool"] == "list_dir" for h in history):

                return {
                    "steps": [
                        {
                            "id": len(history),
                            "tool": "list_dir",
                            "args": {}
                        }
                    ]
                }

            # Step 2: prevent repeated writes
            if last_tool == "write_file":
                return {"done": True, "reason": "file already written"}

            filename = self._extract_filename(goal)
            content = self._generate_content(goal, state)

            return {
                "steps": [
                    {
                        "id": len(history),
                        "tool": "write_file",
                        "args": {
                            "filename": filename,
                            "content": content
                        }
                    }
                ]
            }

        # ====================================================
        # FALLBACK
        # ====================================================

        return {
            "done": True,
            "reason": f"unknown intent: {intent}"
        }

    # ====================================================
    # FILE NAME EXTRACTION (SAFE + SIMPLE)
    # ====================================================

    def _extract_filename(self, goal: str):

        g = goal.lower()

        for token in goal.split():
            if ".txt" in token:
                return token.strip(".,!?")

        if "hello" in g:
            return "hello.txt"

        if "report" in g:
            return "report.txt"

        return "output.txt"

    # ====================================================
    # CRITICAL FIX: STRICT CONTENT GENERATION
    # ====================================================

    def _generate_content(self, goal: str, state: dict):

        g = goal.lower()

        # ----------------------------------------------------
        # RULE 1: explicit "text X"
        # ----------------------------------------------------

        if "text" in g:

            words = goal.split()

            for i, w in enumerate(words):
                if w.lower() == "text" and i + 1 < len(words):
                    return words[i + 1]

            return words[-1]

        # ----------------------------------------------------
        # RULE 2: ONLY summarize if explicitly asked
        # ----------------------------------------------------

        if "summary" in g:

            for h in reversed(state.get("history", [])):

                output = h.get("result", {}).get("output", {})
                items = output.get("items")

                if items:
                    return "Directory summary:\n" + "\n".join(f"- {i}" for i in items)

        # ----------------------------------------------------
        # RULE 3: NO HISTORY LEAKAGE DEFAULT
        # ----------------------------------------------------

        return goal