from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class WorkspaceState:
    """Represents current workspace session state.

    Summary layer only. Does NOT store execution traces, DAGs, or tool outputs.
    """

    def __init__(
        self,
        session_id: str = "",
        name: str = "",
        workspace_root: str = "",
        active_goals: Optional[List[str]] = None,
        blocked_goals: Optional[List[str]] = None,
        created_at: str = "",
        last_opened: str = "",
        recent_commands: Optional[List[str]] = None,
        recent_handoffs: Optional[List[str]] = None,
    ) -> None:
        self.session_id = session_id
        self.name = name
        self.workspace_root = workspace_root
        self.active_goals = list(active_goals or [])
        self.blocked_goals = list(blocked_goals or [])
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.last_opened = last_opened or datetime.now(timezone.utc).isoformat()
        self.recent_commands = list(recent_commands or [])
        self.recent_handoffs = list(recent_handoffs or [])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "workspace_root": self.workspace_root,
            "active_goals": sorted(self.active_goals),
            "blocked_goals": sorted(self.blocked_goals),
            "created_at": self.created_at,
            "last_opened": self.last_opened,
            "recent_commands": list(self.recent_commands[-20:]),
            "recent_handoffs": list(self.recent_handoffs[-10:]),
        }

    @staticmethod
    def from_session_data(session_data: Any) -> WorkspaceState:
        return WorkspaceState(
            session_id=session_data.session_id,
            name=session_data.name,
            workspace_root=session_data.workspace_root,
            active_goals=list(session_data.active_goals),
            blocked_goals=list(session_data.blocked_goals),
            created_at=session_data.created_at,
            last_opened=session_data.last_opened,
            recent_commands=list(session_data.recent_commands),
            recent_handoffs=list(session_data.recent_handoffs),
        )

    def record_command(self, command: str) -> None:
        self.recent_commands.append(command)
        if len(self.recent_commands) > 20:
            self.recent_commands = self.recent_commands[-20:]

    def record_handoff(self, handoff_id: str) -> None:
        self.recent_handoffs.append(handoff_id)
        if len(self.recent_handoffs) > 10:
            self.recent_handoffs = self.recent_handoffs[-10:]
