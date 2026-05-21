import re
from typing import List, Dict, Any


class Planner:
    """
    v0.9 Deterministic Planner

    Responsibilities:
    - Convert constrained natural language into structured steps
    - Enforce deterministic grammar
    - Reject ambiguous or malformed input

    Non-goals:
    - No inference beyond grammar
    - No fallback generation
    - No AI reasoning
    - No repair logic
    """

    def __init__(self):

        self.allowed_tools = {
            "write_file",
            "read_file",
            "list_dir"
        }

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def plan(self, goal: str) -> List[Dict[str, Any]]:

        if not isinstance(goal, str):
            return []

        goal = goal.strip()

        if not goal:
            return []

        lowered = goal.lower()

        if self._is_garbage_input(lowered):
            return []

        raw_steps = re.split(r"\bthen\b", goal, flags=re.IGNORECASE)

        plan = []

        for index, raw_step in enumerate(raw_steps):

            parsed = self._parse_step(raw_step.strip(), index)

            if parsed is None:
                return []

            plan.append(parsed)

        return plan

    # =====================================================
    # GARBAGE DETECTION
    # =====================================================

    def _is_garbage_input(self, text: str) -> bool:

        if '"tool"' in text or '"args"' in text:
            return True

        symbol_ratio = len(re.findall(r'[^a-zA-Z0-9\s]', text)) / max(len(text), 1)

        if symbol_ratio > 0.35:
            return True

        valid_keywords = ["create", "write", "read", "list"]

        if not any(k in text for k in valid_keywords):
            return True

        return False

    # =====================================================
    # STEP PARSING
    # =====================================================

    def _parse_step(self, text: str, index: int):

        cleaned = text.strip()

        # -------------------------------------------------
        # WRITE / CREATE FILE (FIXED: supports quoted + unquoted content)
        # -------------------------------------------------

        write_match = re.search(
            r'(create|write)\s+([a-zA-Z0-9_\-\.]+)\s+with\s+(?:"([^"]*)"|([a-zA-Z0-9_\-]+))',
            cleaned,
            re.IGNORECASE
        )

        if write_match:

            filename = self._clean_filename(write_match.group(2))

            # FIX: support both quoted and unquoted content
            content = write_match.group(3) or write_match.group(4)

            if not filename or content is None:
                return None

            return {
                "tool": "write_file",
                "args": {
                    "filename": filename,
                    "content": content
                },
                "on_fail": "abort",
                "fallback": None,
                "depends_on": [],
                "meta": {
                    "index": index
                }
            }

        # -------------------------------------------------
        # READ FILE
        # -------------------------------------------------

        read_match = re.search(
            r'read\s+([a-zA-Z0-9_\-\.]+)',
            cleaned,
            re.IGNORECASE
        )

        if read_match:

            filename = self._clean_filename(read_match.group(1))

            if not filename:
                return None

            return {
                "tool": "read_file",
                "args": {
                    "filename": filename
                },
                "on_fail": "abort",
                "fallback": None,
                "depends_on": [],
                "meta": {
                    "index": index
                }
            }

        # -------------------------------------------------
        # LIST DIRECTORY
        # -------------------------------------------------

        if re.search(r'list\s+(directory|dir|files)', cleaned, re.IGNORECASE):

            return {
                "tool": "list_dir",
                "args": {},
                "on_fail": "abort",
                "fallback": None,
                "depends_on": [],
                "meta": {
                    "index": index
                }
            }

        return None

    # =====================================================
    # FILENAME CLEANING
    # =====================================================

    def _clean_filename(self, filename: str) -> str:

        filename = filename.strip()

        filename = re.sub(r'[,\.;:]+$', '', filename)

        filename = filename.replace("../", "")
        filename = filename.replace("..\\", "")

        return filename