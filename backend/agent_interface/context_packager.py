from __future__ import annotations

from typing import Any, Dict, Optional

from core.handoff import HandoffBuilder
from core.memory.project_view import ProjectIntelligenceView


class ContextPackager:
    """Sole external memory surface.

    Wraps ProjectIntelligenceView as the only way external interfaces
    access system state. Internal stores (ExecutionMemoryStore, DecisionStore,
    FeedbackStore, GoalRegistry) remain invisible abstractions.

    All API/UI/CLI outputs requesting "system state" must resolve through
    this class only.
    """

    def __init__(self, project_view: Optional[ProjectIntelligenceView] = None) -> None:
        self._pv = project_view
        self._session_info: Dict[str, Any] = {}

    def set_session_info(self, info: Dict[str, Any]) -> None:
        self._session_info = dict(info)

    def get_overview(self) -> Dict[str, Any]:
        if self._pv is None:
            result = {
                "lens": "overview",
                "active_goals": [],
                "blocked_goals": [],
                "completed_goals": [],
                "continuation_links": [],
                "recurring_failures": [],
                "goal_count": {"active": 0, "blocked": 0, "completed": 0, "total": 0},
            }
        else:
            result = self._pv.overview()
        if self._session_info:
            result["workspace_name"] = self._session_info.get("workspace_name", "")
            result["workspace_created"] = self._session_info.get("workspace_created", "")
            result["workspace_last_opened"] = self._session_info.get("workspace_last_opened", "")
            result["workspace_goal_count"] = self._session_info.get("workspace_goal_count", 0)
        return result

    def get_history(self) -> Dict[str, Any]:
        if self._pv is None:
            return {"lens": "history", "entries": []}
        return self._pv.history()

    def get_continuity(self) -> Dict[str, Any]:
        if self._pv is None:
            return {"lens": "continuity", "goal_chains": [], "repeated_attempts": []}
        return self._pv.continuity()

    def get_structure(self) -> Dict[str, Any]:
        if self._pv is None:
            return {
                "lens": "structure", "file_count": 0, "directory_count": 0,
                "extension_breakdown": {}, "components": [],
                "recent_activity": [], "goal_associations": [],
            }
        return self._pv.structure()

    def get_changes(self) -> Dict[str, Any]:
        if self._pv is None:
            return {
                "lens": "changes", "timeline": [],
                "component_activity": [], "goal_activity": [],
            }
        return self._pv.changes()

    def get_relationships(self) -> Dict[str, Any]:
        if self._pv is None:
            return {
                "lens": "relationships",
                "file_relationships": [],
                "component_relationships": [],
                "goal_relationships": [],
            }
        return self._pv.relationships()

    def get_handoff(self, mode: str = "standard") -> Dict[str, Any]:
        builder = HandoffBuilder(project_view=self._pv)
        result = builder.build(mode=mode).to_dict()
        if self._session_info:
            result["workspace"] = {
                "name": self._session_info.get("workspace_name", ""),
                "created_at": self._session_info.get("workspace_created", ""),
                "last_opened": self._session_info.get("workspace_last_opened", ""),
            }
        return result

    def get_handoff_markdown(self, mode: str = "standard") -> str:
        builder = HandoffBuilder(project_view=self._pv)
        return builder.build(mode=mode).to_markdown()

    def get_workspace(self) -> Dict[str, Any]:
        if self._pv is None:
            return {
                "lens": "workspace", "recent_activity": [],
                "active_files": [], "workspace_summary": {},
            }
        return self._pv.workspace()

    def get_lens(self, lens: str = "overview") -> Dict[str, Any]:
        if lens == "history":
            return self.get_history()
        if lens == "continuity":
            return self.get_continuity()
        if lens == "structure":
            return self.get_structure()
        if lens == "changes":
            return self.get_changes()
        if lens == "relationships":
            return self.get_relationships()
        if lens == "workspace":
            return self.get_workspace()
        return self.get_overview()
