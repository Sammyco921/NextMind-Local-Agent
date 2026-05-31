from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class SessionData:
    """Immutable-ish container for a single workspace session's data."""

    def __init__(
        self,
        session_id: str,
        name: str,
        created_at: str,
        last_opened: str,
        workspace_root: str = "",
        active_goals: Optional[List[str]] = None,
        blocked_goals: Optional[List[str]] = None,
        recent_commands: Optional[List[str]] = None,
        recent_handoffs: Optional[List[str]] = None,
        status: str = "active",
    ) -> None:
        self.session_id = session_id
        self.name = name
        self.created_at = created_at
        self.last_opened = last_opened
        self.workspace_root = workspace_root
        self.active_goals = list(active_goals or [])
        self.blocked_goals = list(blocked_goals or [])
        self.recent_commands = list(recent_commands or [])
        self.recent_handoffs = list(recent_handoffs or [])
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "created_at": self.created_at,
            "last_opened": self.last_opened,
            "workspace_root": self.workspace_root,
            "active_goals": sorted(self.active_goals),
            "blocked_goals": sorted(self.blocked_goals),
            "recent_commands": list(self.recent_commands),
            "recent_handoffs": list(self.recent_handoffs),
            "status": self.status,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> SessionData:
        return SessionData(
            session_id=d.get("session_id", ""),
            name=d.get("name", ""),
            created_at=d.get("created_at", ""),
            last_opened=d.get("last_opened", ""),
            workspace_root=d.get("workspace_root", ""),
            active_goals=d.get("active_goals", []),
            blocked_goals=d.get("blocked_goals", []),
            recent_commands=d.get("recent_commands", []),
            recent_handoffs=d.get("recent_handoffs", []),
            status=d.get("status", "active"),
        )


class SessionStore:
    """JSON-backed persistent store for workspace sessions.

    Persists under data/sessions/. No database, no sqlite, no caching,
    no background threads. Deterministic serialization.
    """

    def __init__(self, data_dir: str) -> None:
        self._data_dir = data_dir
        self._file_path = os.path.join(data_dir, "sessions.json")
        self._sessions: Dict[str, SessionData] = {}
        self._load()

    def _ensure_dir(self) -> None:
        os.makedirs(self._data_dir, exist_ok=True)

    def _load(self) -> None:
        self._ensure_dir()
        if not os.path.isfile(self._file_path):
            self._sessions = {}
            return
        try:
            with open(self._file_path, "r") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                self._sessions = {}
                return
            self._sessions = {}
            for sid, data in raw.items():
                self._sessions[sid] = SessionData.from_dict(data)
        except (json.JSONDecodeError, IOError):
            self._sessions = {}

    def _save(self) -> None:
        self._ensure_dir()
        raw: Dict[str, Any] = {}
        for sid, data in self._sessions.items():
            raw[sid] = data.to_dict()
        with open(self._file_path, "w") as f:
            json.dump(raw, f, indent=2, sort_keys=True)

    def create(self, name: str, workspace_root: str = "") -> SessionData:
        now = datetime.now(timezone.utc).isoformat()
        session = SessionData(
            session_id=str(uuid.uuid4())[:8],
            name=name,
            created_at=now,
            last_opened=now,
            workspace_root=workspace_root,
            status="active",
        )
        self._sessions[session.session_id] = session
        self._save()
        return session

    def load(self, session_id: str) -> Optional[SessionData]:
        return self._sessions.get(session_id)

    def load_by_name(self, name: str) -> Optional[SessionData]:
        for s in self._sessions.values():
            if s.name == name and s.status != "archived":
                return s
        return None

    def save(self, session: SessionData) -> None:
        self._sessions[session.session_id] = session
        self._save()

    def list_sessions(self) -> List[SessionData]:
        return [
            s for s in sorted(self._sessions.values(), key=lambda x: x.last_opened, reverse=True)
            if s.status != "archived"
        ]

    def mark_active(self, session_id: str) -> bool:
        s = self._sessions.get(session_id)
        if s is None:
            return False
        s.status = "active"
        s.last_opened = datetime.now(timezone.utc).isoformat()
        self._save()
        return True

    def mark_archived(self, session_id: str) -> bool:
        s = self._sessions.get(session_id)
        if s is None:
            return False
        s.status = "archived"
        self._save()
        return True

    def get_active_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.status == "active")

    @property
    def file_path(self) -> str:
        return self._file_path
