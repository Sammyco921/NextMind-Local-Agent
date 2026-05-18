class Observer:
    """
    v0.5 Observation Layer

    Purpose:
    - Convert raw tool outputs into structured environment state
    - Maintain a lightweight "world model"
    - Provide grounded context to the planner
    """

    def __init__(self):
        self.state = {
            "files": set(),
            "last_outputs": [],
            "facts": [],
            "history_index": 0
        }

    # ====================================================
    # MAIN ENTRY
    # ====================================================

    def update(self, step: dict, result: dict):
        """
        Update observation state from an executed step.
        """

        if not isinstance(step, dict) or not isinstance(result, dict):
            return self.state

        tool = step.get("tool")
        output = result.get("output")

        # ----------------------------------------
        # STORE RAW HISTORY
        # ----------------------------------------
        self.state["last_outputs"].append({
            "step": step,
            "result": result
        })

        # keep bounded memory
        if len(self.state["last_outputs"]) > 20:
            self.state["last_outputs"] = self.state["last_outputs"][-20:]

        # ----------------------------------------
        # TOOL-SPECIFIC OBSERVATIONS
        # ----------------------------------------

        if tool == "write_file":
            self._observe_write(output)

        elif tool == "read_file":
            self._observe_read(output)

        elif tool == "list_dir":
            self._observe_list(output)

        # ----------------------------------------
        # GENERAL FACT EXTRACTION
        # ----------------------------------------
        self._extract_facts(step, result)

        self.state["history_index"] += 1

        return self.state

    # ====================================================
    # TOOL OBSERVATIONS
    # ====================================================

    def _observe_write(self, output):
        if not isinstance(output, dict):
            return

        file = output.get("file")
        if file:
            self.state["files"].add(file)

    def _observe_read(self, output):
        if not isinstance(output, dict):
            return

        file = output.get("file")
        content = output.get("content")

        if file:
            self.state["files"].add(file)

        if content:
            self.state["facts"].append({
                "type": "file_content",
                "file": file,
                "content_preview": content[:200]
            })

    def _observe_list(self, output):
        if not isinstance(output, dict):
            return

        items = output.get("items", [])

        if isinstance(items, list):
            for item in items:
                self.state["files"].add(item)

            self.state["facts"].append({
                "type": "directory_listing",
                "items": items
            })

    # ====================================================
    # GENERAL FACT EXTRACTION
    # ====================================================

    def _extract_facts(self, step, result):
        """
        Lightweight heuristic fact extractor.
        Keeps system extensible without overengineering.
        """

        status = result.get("status")

        self.state["facts"].append({
            "type": "execution_event",
            "tool": step.get("tool"),
            "status": str(status),
            "step_id": step.get("id")
        })

    # ====================================================
    # CONTEXT ACCESSORS
    # ====================================================

    def get_state(self):
        """
        Return full observation state.
        """
        return self.state

    def get_summary(self):
        """
        Lightweight snapshot for planner input.
        """

        return {
            "files": list(self.state["files"]),
            "recent_facts": self.state["facts"][-10:],
            "recent_outputs": self.state["last_outputs"][-5:]
        }

    # ====================================================
    # RESET (for new goals)
    # ====================================================

    def reset(self):
        self.state = {
            "files": set(),
            "last_outputs": [],
            "facts": [],
            "history_index": 0
        }