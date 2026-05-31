from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Set

from core.structure.project_catalog import FileRecord


@dataclass(frozen=True)
class ComponentRule:
    name: str
    match: Callable[[FileRecord], bool]
    description: str = ""


class ComponentRegistry:
    """Deterministic component assignment using explicit rules only.

    Rules use path prefixes, directory location, and extension patterns.
    Never infers component meaning, generates names, or creates semantic labels.
    """

    def __init__(self, rules: Optional[List[ComponentRule]] = None) -> None:
        self._rules: List[ComponentRule] = rules or _DEFAULT_RULES
        self._cache: Dict[str, Optional[str]] = {}

    def assign(self, record: FileRecord) -> Optional[str]:
        key = record.path
        if key in self._cache:
            return self._cache[key]
        for rule in self._rules:
            if rule.match(record):
                self._cache[key] = rule.name
                return rule.name
        self._cache[key] = None
        return None

    def get_components(self) -> List[str]:
        seen: Set[str] = set()
        for rule in self._rules:
            seen.add(rule.name)
        return sorted(seen)

    def get_component_files(
        self, name: str, records: List[FileRecord],
    ) -> List[FileRecord]:
        return [r for r in records if self.assign(r) == name]

    def file_counts(self, records: List[FileRecord]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for r in records:
            comp = self.assign(r)
            if comp:
                counts[comp] = counts.get(comp, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def directory_counts(self, records: List[FileRecord]) -> Dict[str, int]:
        dirs: Dict[str, Set[str]] = {}
        for r in records:
            comp = self.assign(r)
            if comp and r.dir_path:
                dirs.setdefault(comp, set()).add(r.dir_path)
        return {c: len(d) for c, d in sorted(dirs.items(), key=lambda x: -x[1])}


def _make_prefix_rule(prefix: str, name: str, desc: str = "") -> ComponentRule:
    def match(record: FileRecord) -> bool:
        return record.path.startswith(prefix) or record.dir_path.startswith(prefix)
    return ComponentRule(name=name, match=match, description=desc or f"Files under {prefix}")


_DEFAULT_RULES: List[ComponentRule] = [
    _make_prefix_rule("backend/core/", "Core Engine", "Core execution and memory modules"),
    _make_prefix_rule("backend/tools/", "Tools", "File and transformation tools"),
    _make_prefix_rule("backend/tests/", "Tests", "Test suite"),
    _make_prefix_rule("backend/agent_interface/", "Agent Interface", "User-facing interface layer"),
    _make_prefix_rule("backend/config/", "Config", "Configuration files"),
    ComponentRule(
        name="Backend",
        match=lambda r: r.path.startswith("backend/") and not r.is_directory,
        description="Backend application code",
    ),
    _make_prefix_rule("frontend/", "Frontend", "Web UI frontend"),
    ComponentRule(
        name="Logs & Memory",
        match=lambda r: r.path.startswith("backend/logs/") or r.path.startswith("backend/memory/"),
        description="Runtime logs and persistent memory stores",
    ),
]
