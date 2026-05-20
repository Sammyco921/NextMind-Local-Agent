# core/planner.py
#
# NextMind v0.8 — Planner (STRICT MODE FINAL)
#
# Key change:
#   NO FALLBACK EXECUTION UNDER ANY CIRCUMSTANCE
#
# Behavior:
#   - Only produces steps when tool mapping is explicit
#   - Returns empty list for unknown/invalid input
#   - Never defaults to list_dir or any safe tool
#   - Deterministic, non-inferential


from __future__ import annotations

from typing import List, Dict, Any
import re
import json


class Planner:
    """
    Strict deterministic planner.
    """

    # =====================================================
    # ENTRY POINT
    # =====================================================

    def plan(self, goal: str) -> List[Dict[str, Any]]:

        if not isinstance(goal, str):
            return []

        goal = goal.strip()

        if not goal:
            return []

        # -----------------------------
        # JSON PATH
        # -----------------------------
        if self._looks_like_json(goal):
            parsed = self._safe_parse_json(goal)

            if isinstance(parsed, list):
                steps = []
                for i, s in enumerate(parsed):
                    step = self._normalize_step(s, i)
                    if step:
                        steps.append(step)
                return steps

            if isinstance(parsed, dict):
                step = self._normalize_step(parsed, 0)
                return [step] if step else []

            return []

        # -----------------------------
        # NATURAL LANGUAGE PATH
        # -----------------------------
        return self._plan_single(goal)

    # =====================================================
    # STRICT NATURAL LANGUAGE PLANNER
    # =====================================================

    def _plan_single(self, goal: str) -> List[Dict[str, Any]]:

        steps = []

        parts = [p.strip() for p in re.split(r"\bthen\b", goal, flags=re.IGNORECASE)]

        for part in parts:
            if not part:
                continue

            step = self._infer_step(part)

            # STRICT MODE: no inference → no execution
            if step is None:
                return []

            steps.append(step)

        return steps

    # =====================================================
    # STRICT STEP INFERENCE
    # =====================================================

    def _infer_step(self, text: str) -> Dict[str, Any] | None:

        t = text.lower().strip()

        # -------------------------
        # WRITE FILE (STRICT PATTERN)
        # -------------------------
        m = re.search(r"create\s+(\w+\.\w+)\s+with\s+\"(.+?)\"", t)
        if m:
            return self._normalize_step({
                "tool": "write_file",
                "args": {
                    "filename": m.group(1),
                    "content": m.group(2)
                }
            }, 0)

        # -------------------------
        # READ FILE
        # -------------------------
        m = re.search(r"read\s+(\w+\.\w+)", t)
        if m:
            return self._normalize_step({
                "tool": "read_file",
                "args": {
                    "filename": m.group(1)
                }
            }, 0)

        # -------------------------
        # LIST DIRECTORY (EXPLICIT ONLY)
        # -------------------------
        if t in {"list directory", "list files", "show directory"}:
            return self._normalize_step({
                "tool": "list_dir",
                "args": {}
            }, 0)

        # -------------------------
        # NO MATCH = FAILURE (IMPORTANT)
        # -------------------------
        return None

    # =====================================================
    # JSON UTILITIES
    # =====================================================

    def _looks_like_json(self, text: str) -> bool:
        text = text.strip()
        return (text.startswith("{") and text.endswith("}")) or \
               (text.startswith("[") and text.endswith("]"))

    def _safe_parse_json(self, text: str):
        try:
            return json.loads(text)
        except Exception:
            return None

    # =====================================================
    # NORMALIZATION
    # =====================================================

    def _normalize_step(self, step: Dict[str, Any], idx: int) -> Dict[str, Any] | None:

        if not isinstance(step, dict):
            return None

        tool = step.get("tool")
        args = step.get("args")

        if not isinstance(tool, str):
            return None

        if not isinstance(args, dict):
            return None

        return {
            "tool": tool,
            "args": args,
            "on_fail": "abort",
            "fallback": None,
            "depends_on": step.get("depends_on", []),
            "meta": {
                "planned": True,
                "index": idx
            }
        }