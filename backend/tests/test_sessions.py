from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from core.session.session_manager import SessionManager
from core.session.session_store import SessionData, SessionStore
from core.session.workspace_state import WorkspaceState


# ---- SessionData tests ----

class TestSessionData:
    def test_create(self) -> None:
        data = SessionData(
            session_id="abc123",
            name="test-workspace",
            created_at="2025-01-01T00:00:00",
            last_opened="2025-01-01T00:00:00",
        )
        assert data.session_id == "abc123"
        assert data.name == "test-workspace"
        assert data.status == "active"

    def test_to_dict(self) -> None:
        data = SessionData(
            session_id="abc", name="test",
            created_at="2025-01-01T00:00:00",
            last_opened="2025-01-01T00:00:00",
            active_goals=["goal1"],
            blocked_goals=["goal2"],
            recent_commands=["cmd1"],
            recent_handoffs=["h1"],
        )
        d = data.to_dict()
        assert d["session_id"] == "abc"
        assert d["name"] == "test"
        assert d["active_goals"] == ["goal1"]
        assert d["blocked_goals"] == ["goal2"]
        assert d["recent_commands"] == ["cmd1"]
        assert d["status"] == "active"

    def test_from_dict_roundtrip(self) -> None:
        original = SessionData(
            session_id="xyz", name="ws",
            created_at="2025-06-01T00:00:00",
            last_opened="2025-06-01T00:00:00",
            active_goals=["a"], blocked_goals=["b"],
            recent_commands=["c"], recent_handoffs=["d"],
            status="active",
        )
        restored = SessionData.from_dict(original.to_dict())
        assert restored.session_id == original.session_id
        assert restored.name == original.name
        assert restored.active_goals == original.active_goals
        assert restored.blocked_goals == original.blocked_goals
        assert restored.recent_commands == original.recent_commands
        assert restored.recent_handoffs == original.recent_handoffs
        assert restored.status == original.status

    def test_empty_lists_default(self) -> None:
        data = SessionData(
            session_id="a", name="b",
            created_at="", last_opened="",
        )
        assert data.active_goals == []
        assert data.blocked_goals == []
        assert data.recent_commands == []
        assert data.recent_handoffs == []


# ---- SessionStore tests ----

class TestSessionStore:
    @pytest.fixture
    def store(self, tmp_path: Path) -> SessionStore:
        return SessionStore(data_dir=str(tmp_path))

    def test_empty_store(self, store: SessionStore) -> None:
        assert store.list_sessions() == []

    def test_create_session(self, store: SessionStore) -> None:
        session = store.create("test-ws")
        assert session.name == "test-ws"
        assert session.status == "active"
        assert session.session_id != ""

    def test_load_by_id(self, store: SessionStore) -> None:
        created = store.create("ws1")
        loaded = store.load(created.session_id)
        assert loaded is not None
        assert loaded.name == "ws1"

    def test_load_by_name(self, store: SessionStore) -> None:
        store.create("my-workspace")
        loaded = store.load_by_name("my-workspace")
        assert loaded is not None
        assert loaded.name == "my-workspace"

    def test_load_by_name_nonexistent(self, store: SessionStore) -> None:
        assert store.load_by_name("nonexistent") is None

    def test_list_sessions_order(self, store: SessionStore) -> None:
        import time
        s1 = store.create("first")
        time.sleep(0.01)
        s2 = store.create("second")
        sessions = store.list_sessions()
        assert sessions[0].name == "second"
        assert sessions[1].name == "first"

    def test_mark_active_updates_timestamp(self, store: SessionStore) -> None:
        s = store.create("ws")
        old = s.last_opened
        store.mark_active(s.session_id)
        assert store.load(s.session_id).last_opened >= old

    def test_mark_archived(self, store: SessionStore) -> None:
        s = store.create("ws")
        store.mark_archived(s.session_id)
        assert store.load(s.session_id).status == "archived"
        assert store.list_sessions() == []

    def test_mark_active_nonexistent(self, store: SessionStore) -> None:
        assert store.mark_active("nonexistent") is False

    def test_save_updates_session(self, store: SessionStore) -> None:
        s = store.create("ws")
        s.name = "renamed"
        store.save(s)
        assert store.load(s.session_id).name == "renamed"

    def test_json_persistence(self, tmp_path: Path) -> None:
        store1 = SessionStore(data_dir=str(tmp_path))
        store1.create("persist-test")
        store2 = SessionStore(data_dir=str(tmp_path))
        sessions = store2.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].name == "persist-test"

    def test_corrupted_json(self, tmp_path: Path) -> None:
        import json
        sess_dir = tmp_path / "sessions"
        sess_dir.mkdir(parents=True)
        (sess_dir / "sessions.json").write_text("not valid json{{{")
        store = SessionStore(data_dir=str(sess_dir))
        assert store.list_sessions() == []

    def test_deterministic_serialization(self, store: SessionStore) -> None:
        store.create("alpha")
        store.create("beta")
        with open(store.file_path) as f:
            raw1 = f.read()
        with open(store.file_path) as f:
            raw2 = f.read()
        assert raw1 == raw2

    def test_archived_not_in_list(self, store: SessionStore) -> None:
        s = store.create("temp")
        store.mark_archived(s.session_id)
        names = [x.name for x in store.list_sessions()]
        assert "temp" not in names

    def test_load_by_name_ignores_archived(self, store: SessionStore) -> None:
        s = store.create("old")
        store.mark_archived(s.session_id)
        assert store.load_by_name("old") is None


# ---- WorkspaceState tests ----

class TestWorkspaceState:
    def test_create_empty(self) -> None:
        ws = WorkspaceState()
        assert ws.name == ""
        assert ws.active_goals == []
        assert ws.blocked_goals == []
        assert ws.created_at != ""

    def test_to_dict(self) -> None:
        ws = WorkspaceState(
            session_id="s1", name="test",
            active_goals=["g1"], blocked_goals=["g2"],
            recent_commands=["cmd1"], recent_handoffs=["h1"],
        )
        d = ws.to_dict()
        assert d["name"] == "test"
        assert d["active_goals"] == ["g1"]
        assert d["recent_commands"] == ["cmd1"]

    def test_from_session_data(self, tmp_path: Path) -> None:
        store = SessionStore(data_dir=str(tmp_path))
        sd = store.create("ws1")
        ws = WorkspaceState.from_session_data(sd)
        assert ws.name == "ws1"
        assert ws.session_id == sd.session_id

    def test_record_command(self) -> None:
        ws = WorkspaceState()
        ws.record_command("create file")
        assert "create file" in ws.recent_commands
        assert len(ws.recent_commands) == 1

    def test_record_command_caps_at_20(self) -> None:
        ws = WorkspaceState()
        for i in range(25):
            ws.record_command(f"cmd{i}")
        assert len(ws.recent_commands) == 20
        assert ws.recent_commands[-1] == "cmd24"

    def test_record_handoff(self) -> None:
        ws = WorkspaceState()
        ws.record_handoff("handoff-1")
        assert "handoff-1" in ws.recent_handoffs

    def test_record_handoff_caps_at_10(self) -> None:
        ws = WorkspaceState()
        for i in range(15):
            ws.record_handoff(f"h{i}")
        assert len(ws.recent_handoffs) == 10


# ---- SessionManager tests ----

class TestSessionManager:
    @pytest.fixture
    def mgr(self, tmp_path: Path) -> SessionManager:
        return SessionManager(data_dir=str(tmp_path))

    def test_initial_current_is_none(self, mgr: SessionManager) -> None:
        current = mgr.get_current_workspace()
        assert current["name"] == "default"

    def test_create_workspace(self, mgr: SessionManager) -> None:
        result = mgr.create_workspace("my-ws")
        assert result["name"] == "my-ws"
        assert result["session_id"] != ""

    def test_current_after_create(self, mgr: SessionManager) -> None:
        mgr.create_workspace("ws1")
        current = mgr.get_current_workspace()
        assert current["name"] == "ws1"

    def test_switch_workspace(self, mgr: SessionManager) -> None:
        mgr.create_workspace("first")
        mgr.create_workspace("second")
        result = mgr.switch_workspace("first")
        assert result["name"] == "first"

    def test_switch_nonexistent(self, mgr: SessionManager) -> None:
        result = mgr.switch_workspace("ghost")
        assert "error" in result

    def test_list_workspaces(self, mgr: SessionManager) -> None:
        mgr.create_workspace("alpha")
        mgr.create_workspace("beta")
        workspaces = mgr.list_workspaces()
        names = [w["name"] for w in workspaces]
        assert "alpha" in names
        assert "beta" in names

    def test_open_existing_workspace(self, mgr: SessionManager) -> None:
        mgr.create_workspace("existing")
        result = mgr.open_workspace("existing")
        assert result["name"] == "existing"

    def test_open_new_workspace(self, mgr: SessionManager) -> None:
        result = mgr.open_workspace("brand-new")
        assert result["name"] == "brand-new"

    def test_ensure_default_creates_if_needed(self, mgr: SessionManager) -> None:
        mgr.ensure_default()
        current = mgr.get_current_workspace()
        assert current["name"] == "default"

    def test_save_current(self, mgr: SessionManager) -> None:
        mgr.create_workspace("save-test")
        mgr._current_state.record_command("test command")
        mgr.save_current()
        mgr2 = SessionManager(data_dir=mgr._store._data_dir)
        mgr2.open_workspace("save-test")
        assert "test command" in mgr2._current_state.recent_commands

    def test_persistence_across_restart(self, tmp_path: Path) -> None:
        mgr1 = SessionManager(data_dir=str(tmp_path))
        mgr1.create_workspace("persist-ws")
        mgr1.save_current()

        mgr2 = SessionManager(data_dir=str(tmp_path))
        workspaces = mgr2.list_workspaces()
        assert len(workspaces) == 1
        assert workspaces[0]["name"] == "persist-ws"

    def test_record_command_on_manager(self, mgr: SessionManager) -> None:
        mgr.create_workspace("test")
        mgr.record_command("hello")
        assert mgr._current_state.recent_commands == ["hello"]

    def test_get_workspace_info(self, mgr: SessionManager) -> None:
        mgr.create_workspace("info-test")
        info = mgr.get_workspace_info()
        assert info["workspace_name"] == "info-test"
        assert "workspace_created" in info
        assert "workspace_goal_count" in info

    def test_get_workspace_info_before_create(self, mgr: SessionManager) -> None:
        info = mgr.get_workspace_info()
        assert info["workspace_name"] == "default"

    def test_deterministic_list(self, mgr: SessionManager) -> None:
        mgr.create_workspace("a")
        mgr.create_workspace("b")
        l1 = mgr.list_workspaces()
        l2 = mgr.list_workspaces()
        assert l1 == l2
