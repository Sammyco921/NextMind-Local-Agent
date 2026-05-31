from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Ordered replacement rules — first match wins
_ABBREVIATIONS: List[tuple[re.Pattern, str]] = [
    (re.compile(r"\bui\b", re.I), "user interface"),
    (re.compile(r"\bux\b", re.I), "user experience"),
    (re.compile(r"\bpls\b", re.I), "please"),
    (re.compile(r"\bplz\b", re.I), "please"),
    (re.compile(r"\bthx\b", re.I), "thanks"),
    (re.compile(r"\bty\b", re.I), "thank you"),
    (re.compile(r"\bcont\b", re.I), "continue"),
    (re.compile(r"\bproj\b", re.I), "project"),
    (re.compile(r"\bdoc\b", re.I), "document"),
    (re.compile(r"\bdocs\b", re.I), "documents"),
    (re.compile(r"\binfo\b", re.I), "information"),
    (re.compile(r"\bconfig\b", re.I), "configuration"),
    (re.compile(r"\bapp\b", re.I), "application"),
    (re.compile(r"\brepo\b", re.I), "repository"),
    (re.compile(r"\bexe\b", re.I), "execute"),
    (re.compile(r"\btemp\b", re.I), "temporary"),
    (re.compile(r"\bprev\b", re.I), "previous"),
    (re.compile(r"\bcur\b", re.I), "current"),
    (re.compile(r"\bdel\b", re.I), "delete"),
    (re.compile(r"\bdiff\b", re.I), "different"),
    (re.compile(r"\bw/\s"), "with "),
    (re.compile(r"\bw\/o\b"), "without"),
    # Common misspellings
    (re.compile(r"\brecieve\b", re.I), "receive"),
    (re.compile(r"\brecieved\b", re.I), "received"),
    (re.compile(r"\btruely\b", re.I), "truly"),
    (re.compile(r"\bocurrence?\b", re.I), "occurrence"),
    (re.compile(r"\bocured\b", re.I), "occurred"),
    (re.compile(r"\boccured\b", re.I), "occurred"),
    (re.compile(r"\baccomodate\b", re.I), "accommodate"),
    (re.compile(r"\bacomodate\b", re.I), "accommodate"),
    (re.compile(r"\bcaled\b", re.I), "called"),
    (re.compile(r"\bcreat\b", re.I), "create"),
    (re.compile(r"\bwrit\b", re.I), "write"),
    # Contractions
    (re.compile(r"\bdont\b", re.I), "do not"),
    (re.compile(r"\bdon't\b", re.I), "do not"),
    (re.compile(r"\bwont\b", re.I), "will not"),
    (re.compile(r"\bwon't\b", re.I), "will not"),
    (re.compile(r"\bcant\b", re.I), "cannot"),
    (re.compile(r"\bcan't\b", re.I), "cannot"),
    (re.compile(r"\bcouldnt\b", re.I), "could not"),
    (re.compile(r"\bcouldn't\b", re.I), "could not"),
    (re.compile(r"\bwouldnt\b", re.I), "would not"),
    (re.compile(r"\bwouldn't\b", re.I), "would not"),
    (re.compile(r"\bshouldnt\b", re.I), "should not"),
    (re.compile(r"\bshouldn't\b", re.I), "should not"),
    (re.compile(r"\bisnt\b", re.I), "is not"),
    (re.compile(r"\bisn't\b", re.I), "is not"),
    (re.compile(r"\barent\b", re.I), "are not"),
    (re.compile(r"\baren't\b", re.I), "are not"),
    (re.compile(r"\bdoesnt\b", re.I), "does not"),
    (re.compile(r"\bdoesn't\b", re.I), "does not"),
]

# Continuation phrases — matched against lowercased text
_CONTINUATION_PATTERNS: List[re.Pattern] = [
    re.compile(r"^\s*continue\s*$", re.I),
    re.compile(r"^\s*keep\s+going\s*$", re.I),
    re.compile(r"^\s*finish\s+(?:this|the\s+task|the\s+work|it|up)\s*$", re.I),
    re.compile(r"^\s*pick\s+up\s+where\s+(?:we|i)\s+left\s+off\s*$", re.I),
    re.compile(r"^\s*carry\s+on\s*$", re.I),
    re.compile(r"^\s*proceed\s*$", re.I),
    re.compile(r"^\s*resume\s*$", re.I),
    re.compile(r"^\s*next\s*$", re.I),
    re.compile(r"^\s*go\s+(?:ahead|on)\s*$", re.I),
    re.compile(r"^\s*move\s+(?:on|forward|ahead)\s*$", re.I),
]

_VAGUE_CLEANUP = re.compile(r"\b(clean\s*(?:up)?|cleanup|tidy|organize|reorganize|restructure)\b", re.I)
_VAGUE_FIX = re.compile(r"\b(fix|repair|correct)\b", re.I)
_VAGUE_IMPROVE = re.compile(r"\b(improve|enhance|better|polish|refine|upgrade)\b", re.I)


@dataclass(frozen=True)
class NormalizedRequest:
    original: str
    normalized: str
    is_continuation: bool = False
    continuation_source: str | None = None
    transformations: List[str] = field(default_factory=list)


class HumanNormalizer:
    def normalize(
        self,
        text: str,
        active_goal_descriptions: List[str] | None = None,
    ) -> NormalizedRequest:
        raw = (text or "").strip()
        if not raw:
            return NormalizedRequest(original=raw, normalized=raw)

        transformations: List[str] = []
        normalized = raw

        # ---- Continuation detection ----
        active_descs = active_goal_descriptions or []
        for pattern in _CONTINUATION_PATTERNS:
            if pattern.search(normalized):
                if active_descs:
                    transformations.append(f"continuation phrase → active goal: {active_descs[0]}")
                    return NormalizedRequest(
                        original=raw,
                        normalized=active_descs[0],
                        is_continuation=True,
                        continuation_source=active_descs[0],
                        transformations=transformations,
                    )
                # Fallback: generic continuation with no active goals
                transformations.append("continuation phrase with no active goals")
                return NormalizedRequest(
                    original=raw,
                    normalized=raw,
                    is_continuation=False,
                    transformations=transformations,
                )

        # ---- Abbreviation expansion ----
        for pattern, replacement in _ABBREVIATIONS:
            if pattern.search(normalized):
                normalized = pattern.sub(replacement, normalized)
                transformations.append(f"abbreviation: {pattern.pattern} → {replacement}")

        # ---- Vague directive → specific tool phrasing ----
        # "clean up the project" → "list directory"
        if _VAGUE_CLEANUP.search(normalized) and not re.search(
            r"\b(?:create|write|read)\b", normalized, re.I
        ):
            normalized = f"list directory: {normalized}"
            transformations.append("vague cleanup → list directory")

        # "fix the ui" → "write file for user interface" after abbreviation expansion
        # Already handled by abbreviation expansion + tool keywords

        # ---- Normalize whitespace ----
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # ---- Normalize punctuation ----
        normalized = normalized.rstrip(".,;:!?")

        return NormalizedRequest(
            original=raw,
            normalized=normalized,
            transformations=transformations,
        )
