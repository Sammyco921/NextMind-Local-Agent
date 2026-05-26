# core/goal_spec.py
#
# Lossless goal representation for fidelity checks (v1.9).

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

_PATH_PATTERN = re.compile(
    r"(src/[\w./-]+\.(?:txt|md|json)|[\w./-]+\.(?:txt|md|json))",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GoalSpec:
    """Exact goal artifacts — used for pre/post fidelity validation."""

    raw_goal: str
    nl_steps: List[str]
    explicit_paths: List[str]
    intent_type: str
    step_count: int

    @classmethod
    def from_goal(cls, raw_goal: str, nl_steps: List[str], intent_type: str) -> "GoalSpec":
        paths: List[str] = []
        seen: set[str] = set()
        for match in _PATH_PATTERN.finditer(raw_goal):
            path = match.group(1)
            if path not in seen:
                paths.append(path)
                seen.add(path)
        paths = _prefer_longest_paths(paths)
        return cls(
            raw_goal=raw_goal,
            nl_steps=list(nl_steps),
            explicit_paths=paths,
            intent_type=intent_type,
            step_count=len(nl_steps),
        )


def _prefer_longest_paths(paths: List[str]) -> List[str]:
    """Drop bare filenames when a longer path in the list already contains them."""
    if not paths:
        return paths
    kept: List[str] = []
    for p in paths:
        basename = p.split("/")[-1]
        if p == basename and any(
            other != p and other.endswith("/" + basename) for other in paths
        ):
            continue
        kept.append(p)
    return kept


def extract_nl_steps(goal: str) -> List[str]:
    """Extract numbered steps preserving order; single block if unnumbered."""
    raw = goal.strip()
    if not raw:
        return []
    normalized = raw.replace("\r\n", "\n").replace("\n", " ")
    parts = re.split(r"\d+\.\s", normalized)
    steps = [p.strip() for p in parts if p.strip()]
    if not steps:
        return [raw]
    return steps
