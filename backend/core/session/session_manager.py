from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.session.session_store import SessionData, SessionStore
from core.session.workspace_state import WorkspaceState


class SessionManager:
    """Manages workspace sessions: open, create, load, save, switch.

    All actions are explicit, no auto-merging, no auto-repair, no inference.
    Pure state persistence layer.
    """

    def __init__(self, data_dir: str) -> None:
        self._store = SessionStore(data_dir=data_dir)
        self._current_state: WorkspaceState | None = None
        self._default_name = "default"

    @property
    def current(self) -> WorkspaceState | None:
        return self._current_state

    def get_current_workspace(self) -> Dict[str, Any]:
        if self._current_state is None:
            return {"name": "default", "session_id": "", "workspace_root": "", "active_goals": [], "blocked_goals": [], "created_at": "", "last_opened": ""}
        return self._current_state.to_dict()

    def list_workspaces(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._store.list_sessions()]

    def create_workspace(self, name: str, workspace_root: str = "") -> Dict[str, Any]:
        session = self._store.create(name=name, workspace_root=workspace_root)
        self._current_state = WorkspaceState.from_session_data(session)
        return self._current_state.to_dict()

    def switch_workspace(self, name: str) -> Dict[str, Any]:
        session = self._store.load_by_name(name)
        if session is None:
            return {"error": f"Workspace '{name}' not found"}
        self._store.mark_active(session.session_id)
        self._current_state = WorkspaceState.from_session_data(session)
        return self._current_state.to_dict()

    def open_workspace(self, name: str) -> Dict[str, Any]:
        session = self._store.load_by_name(name)
        if session is not None:
            self._store.mark_active(session.session_id)
            self._current_state = WorkspaceState.from_session_data(session)
        else:
            session = self._store.create(name=name)
            self._current_state = WorkspaceState.from_session_data(session)
        return self._current_state.to_dict()

    def save_current(self) -> None:
        if self._current_state is None:
            return
        session = self._store.load(self._current_state.session_id)
        if session is None:
            return
        session.name = self._current_state.name
        session.workspace_root = self._current_state.workspace_root
        session.active_goals = list(self._current_state.active_goals)
        session.blocked_goals = list(self._current_state.blocked_goals)
        session.recent_commands = list(self._current_state.recent_commands)
        session.recent_handoffs = list(self._current_state.recent_handoffs)
        session.last_opened = datetime.now(timezone.utc).isoformat()
        self._store.save(session)

    def ensure_default(self) -> None:
        if self._current_state is not None:
            return
        self.open_workspace(self._default_name)

    def record_command(self, command: str) -> None:
        if self._current_state is not None:
            self._current_state.record_command(command)

    def record_handoff(self, handoff_id: str) -> None:
        if self._current_state is not None:
            self._current_state.record_handoff(handoff_id)

    def get_workspace_info(self) -> Dict[str, Any]:
        self.ensure_default()
        if self._current_state is None:
            return {"workspace_name": "default", "workspace_created": "", "workspace_last_opened": "", "workspace_goal_count": 0}
        return {
            "workspace_name": self._current_state.name,
            "workspace_created": self._current_state.created_at,
            "workspace_last_opened": self._current_state.last_opened,
            "workspace_goal_count": len(self._current_state.active_goals) + len(self._current_state.blocked_goals),
        }
