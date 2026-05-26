# core/intent_classifier.py
#
# Intent compiler entry: classify goals before parsing or decomposition.

from __future__ import annotations

import re

from core.planning_types import IntentClassification, IntentType

_COMPLEX_KEYWORDS = frozenset({
    "pipeline",
    "workflow",
    "workflows",
    "system",
    "architecture",
    "deterministic",
    "framework",
    "orchestrat",
    "infrastructure",
    "engine",
    "compiler",
    "dag execution",
    "execution pipeline",
    "multi-step",
    "multistep",
    "end-to-end",
    "e2e",
    "microservice",
    "distributed",
    "abstract",
    "design pattern",
})

_SIMPLE_TOOL_PATTERNS = (
    re.compile(r"\b(create|write|make)\b.*\.(txt|md|json)", re.I),
    re.compile(r"\b(read|open)\b.*\.(txt|md|json)", re.I),
    re.compile(r"\blist\b.*\b(files?|dir|directory|folder)\b", re.I),
    re.compile(r'\b(create|write)\b.*"[^"]+"', re.I),
    re.compile(r"\d+\.\s*(create|read|list|write)\b", re.I),
)


class IntentClassifier:
    """Heuristic intent compiler: simple file/tool ops vs complex system-level tasks."""

    @classmethod
    def classify(cls, goal: str) -> IntentClassification:
        raw = (goal or "").strip()
        if not raw:
            return {
                "type": "complex",
                "raw_goal": raw,
                "requires_decomposition": True,
            }

        lowered = raw.lower()
        intent_type: IntentType = cls._resolve_type(lowered, raw)
        return {
            "type": intent_type,
            "raw_goal": raw,
            "requires_decomposition": intent_type == "complex",
        }

    @classmethod
    def _resolve_type(cls, lowered: str, raw: str) -> IntentType:
        if cls._has_complex_signals(lowered, raw):
            return "complex"

        if cls._looks_like_numbered_file_ops(raw):
            return "simple"

        if any(p.search(raw) for p in _SIMPLE_TOOL_PATTERNS):
            return "simple"

        if cls._is_short_file_operation(lowered):
            return "simple"

        # Abstract goals without concrete file/tool anchors → complex
        if len(lowered.split()) >= 8 and not cls._has_file_anchors(lowered):
            return "complex"

        return "simple"

    @staticmethod
    def _has_complex_signals(lowered: str, raw: str) -> bool:
        for kw in _COMPLEX_KEYWORDS:
            if kw in lowered:
                return True
        if re.search(r"\b(build|design|implement)\b.*\b(system|pipeline|framework)\b", lowered):
            return True
        if re.search(r"\b\d+\.\s", raw) and any(kw in lowered for kw in ("pipeline", "architecture", "framework")):
            return True
        return False

    @staticmethod
    def _looks_like_numbered_file_ops(raw: str) -> bool:
        parts = re.split(r"\d+\.\s", raw.replace("\n", " "))
        steps = [p.strip() for p in parts if p.strip()]
        if len(steps) < 2:
            return False
        file_verbs = ("create", "read", "list", "write", "combine")
        matched = sum(
            1 for s in steps if any(v in s.lower() for v in file_verbs)
        )
        return matched >= len(steps) * 0.6

    @staticmethod
    def _is_short_file_operation(lowered: str) -> bool:
        tokens = lowered.split()
        if len(tokens) > 25:
            return False
        file_ops = ("create", "read", "list", "write", "file", "directory", "folder")
        return sum(1 for t in file_ops if t in lowered) >= 2

    @staticmethod
    def _has_file_anchors(lowered: str) -> bool:
        return bool(
            re.search(r"\.(txt|md|json|py)", lowered)
            or "src/" in lowered
            or "file" in lowered
        )
