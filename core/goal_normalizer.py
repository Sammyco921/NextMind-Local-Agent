# core/goal_normalizer.py
#
# v1.9.1: permissive NL → pseudo-steps. Never enforces semantic correctness.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Deterministic typo normalization (not semantic inference)
_TYPO_REPLACEMENTS = (
    (re.compile(r"\bcrete\b", re.I), "create"),
    (re.compile(r"\bcobine\b", re.I), "combine"),
    (re.compile(r"\bnre\b", re.I), "new"),
    (re.compile(r"\binder\b", re.I), "under"),
    (re.compile(r"\bith\b", re.I), "with"),
    (re.compile(r"\bcaled\b", re.I), "called"),
)

_PATH_RE = re.compile(
    r"(?:"
    r"(?:workspace|src|\.)/[\w./-]+|"
    r"[\w]+/[\w./-]+\.(?:txt|md|json)|"
    r"[\w./-]+\.(?:txt|md|json)"
    r")",
    re.IGNORECASE,
)

_GARBAGE_RE = re.compile(r"^[\s\W\d]+$")


@dataclass
class NormalizedStep:
    text: str
    type_guess: str = "unknown"
    entities: Dict[str, Any] = field(default_factory=dict)
    index: int = 0


@dataclass
class NormalizedGoal:
    raw_goal: str
    normalized_steps: List[NormalizedStep]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "raw_goal": self.raw_goal,
            "normalized_steps": [
                {
                    "text": s.text,
                    "type_guess": s.type_guess,
                    "entities": s.entities,
                }
                for s in self.normalized_steps
            ],
            "warnings": self.warnings,
        }


class GoalNormalizer:
    """
    Convert natural language into structured pseudo-steps.
    Does NOT validate quotes, dependencies, or tool correctness.
    """

    def normalize(self, goal: str) -> NormalizedGoal:
        raw = (goal or "").strip()
        if not raw:
            return NormalizedGoal(raw_goal="", normalized_steps=[])

        if _GARBAGE_RE.match(raw):
            return NormalizedGoal(
                raw_goal=raw,
                normalized_steps=[],
                warnings=["Input is not interpretable text"],
            )

        text = self._apply_typos(raw)
        chunks = self._split_steps(text)
        warnings: List[str] = []
        steps: List[NormalizedStep] = []

        for i, chunk in enumerate(chunks):
            type_guess = self._guess_type(chunk)
            entities = self._extract_entities(chunk, type_guess)
            if type_guess == "unknown":
                warnings.append(f"Step {i + 1}: unrecognized phrasing (kept as text)")
            steps.append(
                NormalizedStep(
                    text=chunk,
                    type_guess=type_guess,
                    entities=entities,
                    index=i,
                )
            )

        return NormalizedGoal(
            raw_goal=raw,
            normalized_steps=steps,
            warnings=warnings,
        )

    @staticmethod
    def _apply_typos(text: str) -> str:
        out = text
        for pattern, replacement in _TYPO_REPLACEMENTS:
            out = pattern.sub(replacement, out)
        return out

    @staticmethod
    def _split_steps(text: str) -> List[str]:
        normalized = text.replace("\r\n", "\n")
        numbered = re.split(r"\d+\.\s+", normalized)
        parts = [p.strip() for p in numbered if p.strip()]
        if len(parts) > 1:
            return parts

        lines = [ln.strip() for ln in normalized.split("\n") if ln.strip()]
        if len(lines) > 1:
            return lines

        if ";" in text:
            semi = [p.strip() for p in text.split(";") if p.strip()]
            if len(semi) > 1:
                return semi

        if re.search(r"\band then\b", text, re.I):
            return [p.strip() for p in re.split(r"\band then\b", text, flags=re.I) if p.strip()]

        if re.search(r"\band read\b", text, re.I):
            return [p.strip() for p in re.split(r"\band\b", text, flags=re.I) if p.strip()]

        return [text.strip()]

    @staticmethod
    def _guess_type(text: str) -> str:
        lower = text.lower()
        if re.search(r"\b(create|make)\b.*\b(directory|dir|folder)\b", lower):
            return "create_dir"
        if any(w in lower for w in ("combine", "merge", "concat")):
            return "combine"
        if re.search(r"\b(read|open)\b", lower) and "file" in lower or _PATH_RE.search(text):
            if "read" in lower:
                return "read_file"
        if re.search(r"\blist\b", lower) and re.search(
            r"\b(directory|dir|folder|files)\b", lower
        ):
            return "list_dir"
        if any(w in lower for w in ("create", "write", "save", "file", "document")):
            return "write_file"
        if "read" in lower:
            return "read_file"
        return "unknown"

    def _extract_entities(self, text: str, type_guess: str) -> Dict[str, Any]:
        entities: Dict[str, Any] = {}
        paths = _PATH_RE.findall(text)
        if paths:
            entities["paths"] = paths
            files = [p for p in paths if re.search(r"\.\w+$", p)]
            if files:
                entities["filename"] = files[0]
                entities["filenames"] = files
            dirs = [p for p in paths if not re.search(r"\.\w+$", p)]
            if dirs:
                entities["directory"] = dirs[0].rstrip("/")

        dir_ctx = re.search(
            r"(?:under|in|into|to)\s+([\w./-]+/?)",
            text,
            re.I,
        )
        called_file = re.search(
            r"(?:called|named)\s+([\w./-]+\.(?:txt|md|json))",
            text,
            re.I,
        )
        if dir_ctx and called_file:
            base = dir_ctx.group(1).rstrip("/")
            entities["filename"] = f"{base}/{called_file.group(1)}"
            entities.setdefault("filenames", []).append(entities["filename"])

        content = self._extract_content(text)
        if content is not None:
            entities["content"] = content

        if type_guess == "combine":
            names = re.findall(r"[\w./-]+\.txt", text, re.I)
            if names:
                entities["source_files"] = names
            out = re.search(
                r"(?:into|to|called)\s+(?:a\s+)?(?:new\s+)?(?:document\s+)?([\w./-]+\.txt)",
                text,
                re.I,
            )
            if out:
                entities["output_file"] = out.group(1)

        return entities

    @staticmethod
    def _extract_content(text: str) -> Optional[str]:
        quoted = re.search(r'"([^"]*)"', text)
        if quoted:
            return quoted.group(1)
        quoted_single = re.search(r"'([^']*)'", text)
        if quoted_single:
            return quoted_single.group(1)
        for pattern in (
            r"(?:exact\s+)?content\s*:\s*(.+)$",
            r"with\s+(?:the\s+)?(?:exact\s+)?content\s*:\s*(.+)$",
            r"with\s+content\s+(.+)$",
            r"content\s+(.+)$",
        ):
            m = re.search(pattern, text, re.I)
            if m:
                return m.group(1).strip().strip('"').strip("'")
        return None
