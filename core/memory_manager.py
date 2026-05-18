import json
import os
import time


class MemoryManager:

    def __init__(self, path="memory/memory_store.json"):
        self.path = path
        self.memory = self._load()

    # ====================================================
    # LOAD / SAVE
    # ====================================================

    def _load(self):

        if not os.path.exists(self.path):
            return {
                "episodic": [],
                "tasks": [],
                "errors": []
            }

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)

        except Exception:
            # corrupt memory fallback
            return {
                "episodic": [],
                "tasks": [],
                "errors": []
            }

    def _save(self):

        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=2)

    # ====================================================
    # CORE WRITE API
    # ====================================================

    def add_episodic(self, event: dict):

        self.memory["episodic"].append({
            "timestamp": time.time(),
            "event": event
        })

        self._save()

    def add_task(self, goal: str, result: dict):

        self.memory["tasks"].append({
            "timestamp": time.time(),
            "goal": goal,
            "result": result
        })

        self._save()

    def add_error(self, error: dict):

        self.memory["errors"].append({
            "timestamp": time.time(),
            "error": error
        })

        self._save()

    # ====================================================
    # RETRIEVAL (SIMPLE BUT EFFECTIVE)
    # ====================================================

    def get_recent_tasks(self, n=5):

        return self.memory["tasks"][-n:]

    def get_recent_errors(self, n=5):

        return self.memory["errors"][-n:]

    def get_recent_events(self, n=5):

        return self.memory["episodic"][-n:]

    # ====================================================
    # CONTEXT BUILDING (FOR PLANNER)
    # ====================================================

    def build_context(self):

        return {
            "recent_tasks": self.get_recent_tasks(),
            "recent_errors": self.get_recent_errors(),
            "recent_events": self.get_recent_events()
        }

    # ====================================================
    # SEARCH (VERY SIMPLE VERSION)
    # ====================================================

    def search(self, keyword: str):

        keyword = keyword.lower()

        matches = []

        for task in self.memory["tasks"]:
            if keyword in task.get("goal", "").lower():
                matches.append(task)

        for error in self.memory["errors"]:
            if keyword in str(error).lower():
                matches.append(error)

        return matches

    # ====================================================
    # CLEAR MEMORY (DEBUG TOOL)
    # ====================================================

    def clear(self):

        self.memory = {
            "episodic": [],
            "tasks": [],
            "errors": []
        }

        self._save()
