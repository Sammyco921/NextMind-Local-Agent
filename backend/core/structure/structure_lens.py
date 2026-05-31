from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.structure.project_catalog import FileRecord, ProjectCatalog
from core.structure.component_registry import ComponentRegistry
from core.structure.goal_impact_tracker import GoalImpactTracker


class StructureLens:
    """Composed read-model over ProjectCatalog, ComponentRegistry, and GoalImpactTracker.

    Produces the "structure" view for ProjectIntelligenceView.
    Deterministic, no inference, no mutation of underlying data sources.
    """

    def __init__(
        self,
        catalog: Optional[ProjectCatalog] = None,
        registry: Optional[ComponentRegistry] = None,
        impact: Optional[GoalImpactTracker] = None,
    ) -> None:
        self._catalog = catalog
        self._registry = registry
        self._impact = impact

    def build(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "lens": "structure",
        }

        files = self._catalog.get_files() if self._catalog else []
        dirs = self._catalog.get_directories() if self._catalog else []

        result["file_count"] = len(files)
        result["directory_count"] = len(dirs)

        result["extension_breakdown"] = (
            self._catalog.get_extension_counts() if self._catalog else {}
        )

        result["components"] = self._build_components(files)

        result["recent_activity"] = self._build_recent_activity()

        result["goal_associations"] = self._build_goal_associations()

        return result

    def _build_components(self, files: List[FileRecord]) -> List[Dict[str, Any]]:
        if self._registry is None:
            return []

        comp_list: List[Dict[str, Any]] = []
        for name in self._registry.get_components():
            comp_files = self._registry.get_component_files(name, files)
            dir_set: set = set()
            for f in comp_files:
                if f.dir_path:
                    dir_set.add(f.dir_path)
            comp_list.append({
                "name": name,
                "file_count": len(comp_files),
                "directory_count": len(dir_set),
            })
        return comp_list

    def _build_recent_activity(self) -> List[Dict[str, Any]]:
        if self._impact is None:
            return []

        recent = self._impact.get_recent_activity(count=20)
        seen: set = set()
        deduped: list = []
        for r in recent:
            key = (r.goal_id, r.file_path)
            if key not in seen:
                seen.add(key)
                deduped.append({
                    "goal_id": r.goal_id,
                    "goal_description": r.goal_description[:80],
                    "file_path": r.file_path,
                    "component": r.component or "",
                    "action": r.action,
                    "timestamp": r.timestamp,
                })
        return deduped

    def _build_goal_associations(self) -> List[Dict[str, Any]]:
        if self._impact is None or self._registry is None:
            return []

        components = self._registry.get_components()
        associations: List[Dict[str, Any]] = []
        for comp in components:
            impacts = self._impact.get_goals_for_component(comp)
            if impacts:
                goal_set: dict = {}
                for imp in impacts:
                    if imp.goal_id not in goal_set:
                        goal_set[imp.goal_id] = {
                            "goal_id": imp.goal_id,
                            "description": imp.goal_description[:80],
                        }
                associations.append({
                    "component": comp,
                    "goals": list(goal_set.values()),
                    "total_goals": len(goal_set),
                })
        return associations
