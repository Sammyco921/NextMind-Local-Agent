# core/planner.py
#
# NextMind v0.7 — Planner
#
# Role:
#   Convert natural language goals into structured execution steps.
#
# Important:
#   - Planner DOES NOT execute
#   - Planner DOES NOT validate safety
#   - Planner ONLY expresses intent
#
# Downstream systems:
#   PipelineValidator -> Scheduler -> Executor


from __future__ import annotations

from typing import List, Dict, Any, Optional
import re
import json


class Planner:
    """
    Structured deterministic planner.
    """

    def __init__(self, intent_router=None):
        self.intent_router = intent_router

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def plan(self, goal: str) -> List[Dict[str, Any]]:
        goal = (goal or "").strip()

        if not goal:
            return []

        # optional external routing
        if self.intent_router:
            try:
                routed = self.intent_router.route(goal)
                if routed:
                    return self._normalize(routed)
            except Exception:
                pass

        # sequence detection
        if self._is_sequence(goal):
            return self._plan_sequence(goal)

        # multi-file creation
        if self._is_multi_file(goal):
            return self._plan_multi_file(goal)

        # JSON creation intent
        if self._looks_like_json(goal):
            return self._plan_json(goal)

        # single action
        return self._normalize([
            self._plan_single(goal)
        ])

    # =====================================================
    # SEQUENCE HANDLING
    # =====================================================

    def _is_sequence(self, text: str) -> bool:
        t = text.lower()

        return any(x in t for x in [
            " then ",
            " and then ",
            " after that ",
        ])

    def _plan_sequence(self, text: str) -> List[Dict[str, Any]]:
        parts = re.split(
            r"\bthen\b|\band then\b|\bafter that\b",
            text,
            flags=re.I
        )

        steps = []

        for p in parts:
            p = p.strip()

            if not p:
                continue

            steps.append(self._plan_single(p))

        return self._normalize(steps)

    # =====================================================
    # MULTI-FILE
    # =====================================================

    def _is_multi_file(self, text: str) -> bool:
        matches = re.findall(
            r"[a-zA-Z0-9_\-]+\.(txt|md|json)",
            text
        )

        return len(matches) > 1

    def _plan_multi_file(self, text: str) -> List[Dict[str, Any]]:
        matches = re.findall(
            r"([a-zA-Z0-9_\-]+\.(?:txt|md|json))",
            text
        )

        steps = []

        for filename in matches:
            ext = filename.split(".")[-1]

            if ext == "md":
                content = f"# {filename.split('.')[0]}"
            elif ext == "json":
                content = "{}"
            else:
                content = ""

            steps.append({
                "tool": "write_file",
                "args": {
                    "filename": filename,
                    "content": content,
                },
                "on_fail": None,
                "fallback": None,
                "depends_on": [],
            })

        return self._normalize(steps)

    # =====================================================
    # JSON INTENT
    # =====================================================

    def _looks_like_json(self, text: str) -> bool:
        return "{" in text and "}" in text

    def _extract_json(self, text: str) -> Optional[dict]:
        try:
            match = re.search(r"\{.*\}", text)

            if not match:
                return None

            return json.loads(match.group(0))

        except Exception:
            return None

    def _plan_json(self, text: str) -> List[Dict[str, Any]]:
        data = self._extract_json(text)

        if data is None:
            return self._normalize([
                self._plan_single(text)
            ])

        filename = self._extract_filename(text)

        return self._normalize([
            {
                "tool": "write_file",
                "args": {
                    "filename": filename,
                    "content": json.dumps(data, indent=2),
                },
                "on_fail": None,
                "fallback": None,
                "depends_on": [],
            }
        ])

    # =====================================================
    # SINGLE STEP
    # =====================================================

    def _plan_single(self, text: str) -> Dict[str, Any]:
        t = text.lower()

        filename = self._extract_filename(text)
        content = self._extract_content(text)

        # -----------------------------
        # WRITE FILE
        # -----------------------------

        if any(k in t for k in [
            "create",
            "write",
            "make",
            "generate",
        ]):
            return {
                "tool": "write_file",
                "args": {
                    "filename": filename,
                    "content": content,
                },
                "on_fail": "abort",
                "fallback": None,
                "depends_on": [],
            }

        # -----------------------------
        # READ FILE
        # -----------------------------

        if any(k in t for k in [
            "read",
            "show",
            "open",
        ]):
            return {
                "tool": "read_file",
                "args": {
                    "filename": filename,
                },
                "on_fail": "continue",
                "fallback": None,
                "depends_on": [],
            }

        # -----------------------------
        # LIST DIRECTORY
        # -----------------------------

        if any(k in t for k in [
            "list",
            "directory",
            "files",
        ]):
            return {
                "tool": "list_dir",
                "args": {},
                "on_fail": "abort",
                "fallback": None,
                "depends_on": [],
            }

        # -----------------------------
        # SAFE DEFAULT
        # -----------------------------

        return {
            "tool": "list_dir",
            "args": {},
            "on_fail": "abort",
            "fallback": None,
            "depends_on": [],
        }

    # =====================================================
    # NORMALIZATION
    # =====================================================

    def _normalize(
        self,
        steps: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:

        normalized = []

        for s in steps:
            normalized.append({
                "tool": s.get("tool", ""),
                "args": s.get("args", {}) or {},
                "on_fail": s.get("on_fail"),
                "fallback": s.get("fallback"),
                "depends_on": s.get("depends_on") or [],
            })

        return normalized

    # =====================================================
    # HELPERS
    # =====================================================

    def _extract_filename(self, text: str) -> str:
        match = re.search(
            r"([a-zA-Z0-9_\-]+\.(?:txt|md|json))",
            text
        )

        if match:
            return match.group(1)

        return "output.txt"

    def _extract_content(self, text: str) -> str:
        quoted = re.findall(r'"(.*?)"', text)

        if quoted:
            return quoted[-1]

        return ""