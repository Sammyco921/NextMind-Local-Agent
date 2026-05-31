from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from core.structure.change_store import ChangeRecord, ChangeStore
from core.structure.change_lens import ChangeLens


# ============================================================
# ChangeRecord Tests
# ============================================================

class TestChangeRecord:
    def test_to_dict_roundtrip(self) -> None:
        rec = ChangeRecord(
            change_id="abc123",
            timestamp="2025-01-01T00:00:00",
            goal_id="g1",
            goal_description="test goal",
            file_path="src/main.py",
            component="Core Engine",
            action_type="modified",
            tool="write_file",
        )
        d = rec.to_dict()
        restored = ChangeRecord.from_dict(d)
        assert restored.change_id == "abc123"
        assert restored.timestamp == "2025-01-01T00:00:00"
        assert restored.goal_id == "g1"
        assert restored.goal_description == "test goal"
        assert restored.file_path == "src/main.py"
        assert restored.component == "Core Engine"
        assert restored.action_type == "modified"
        assert restored.tool == "write_file"

    def test_from_dict_optional_component(self) -> None:
        d = {
            "change_id": "x",
            "timestamp": "2025-01-01T00:00:00",
            "goal_id": "g1",
            "goal_description": "desc",
            "file_path": "f.txt",
            "component": None,
            "action_type": "created",
            "tool": "",
        }
        rec = ChangeRecord.from_dict(d)
        assert rec.component is None
        assert rec.action_type == "created"

    def test_from_dict_missing_fields(self) -> None:
        d: dict = {}
        rec = ChangeRecord.from_dict(d)
        assert rec.change_id == ""
        assert rec.action_type == "modified"


# ============================================================
# ChangeStore Tests
# ============================================================

class TestChangeStore:
    def test_empty_store(self) -> None:
        store = ChangeStore()
        assert store.get_all() == []
        assert store.get_timeline() == []
        assert store.get_by_goal("x") == []
        assert store.get_by_component("y") == []

    def test_record_change(self) -> None:
        store = ChangeStore()
        rec = store.record_change(
            goal_id="g1",
            goal_description="add feature",
            file_path="src/main.py",
            action_type="modified",
            component="Core Engine",
            tool="write_file",
        )
        assert rec.goal_id == "g1"
        assert rec.file_path == "src/main.py"
        assert rec.action_type == "modified"
        assert rec.component == "Core Engine"
        assert rec.tool == "write_file"
        assert rec.change_id != ""
        assert rec.timestamp != ""

    def test_record_change_defaults(self) -> None:
        store = ChangeStore()
        rec = store.record_change(
            goal_id="g1", goal_description="desc", file_path="f.txt",
        )
        assert rec.action_type == "modified"

    def test_record_change_invalid_action_defaults(self) -> None:
        store = ChangeStore()
        rec = store.record_change(
            goal_id="g1", goal_description="desc", file_path="f.txt",
            action_type="invalid",
        )
        assert rec.action_type == "modified"

    def test_get_by_goal(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="a", file_path="f1.txt")
        store.record_change(goal_id="g2", goal_description="b", file_path="f2.txt")
        store.record_change(goal_id="g1", goal_description="c", file_path="f3.txt")
        g1_records = store.get_by_goal("g1")
        assert len(g1_records) == 2
        g2_records = store.get_by_goal("g2")
        assert len(g2_records) == 1

    def test_get_by_component(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="a", file_path="f1.txt", component="Core")
        store.record_change(goal_id="g2", goal_description="b", file_path="f2.txt", component="Tests")
        store.record_change(goal_id="g3", goal_description="c", file_path="f3.txt", component="Core")
        assert len(store.get_by_component("Core")) == 2
        assert len(store.get_by_component("Tests")) == 1
        assert len(store.get_by_component("Nonexistent")) == 0

    def test_get_by_file(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="a", file_path="f1.txt")
        store.record_change(goal_id="g2", goal_description="b", file_path="f1.txt")
        store.record_change(goal_id="g3", goal_description="c", file_path="f2.txt")
        assert len(store.get_by_file("f1.txt")) == 2
        assert len(store.get_by_file("f2.txt")) == 1

    def test_timeline_chronological(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="first", file_path="a.txt")
        store.record_change(goal_id="g2", goal_description="second", file_path="b.txt")
        store.record_change(goal_id="g3", goal_description="third", file_path="c.txt")
        timeline = store.get_timeline(count=10)
        assert len(timeline) == 3
        # most recent first
        assert timeline[0].goal_description == "third"
        assert timeline[2].goal_description == "first"

    def test_timeline_count(self) -> None:
        store = ChangeStore()
        for i in range(10):
            store.record_change(goal_id=f"g{i}", goal_description=str(i), file_path=f"f{i}.txt")
        assert len(store.get_timeline(count=5)) == 5
        assert len(store.get_timeline(count=20)) == 10

    def test_get_components_affected(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="a", file_path="f1.txt", component="Core")
        store.record_change(goal_id="g2", goal_description="b", file_path="f2.txt", component=None)
        store.record_change(goal_id="g3", goal_description="c", file_path="f3.txt", component="Tests")
        comps = store.get_components_affected()
        assert "Core" in comps
        assert "Tests" in comps
        assert None in comps

    def test_store_clear(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="a", file_path="f1.txt")
        assert len(store.get_all()) == 1
        store.clear()
        assert store.get_all() == []

    def test_goal_description_truncated(self) -> None:
        store = ChangeStore()
        long_desc = "x" * 200
        rec = store.record_change(goal_id="g1", goal_description=long_desc, file_path="f.txt")
        assert len(rec.goal_description) == 120

    def test_record_change_returns_record(self) -> None:
        store = ChangeStore()
        rec = store.record_change(
            goal_id="g1", goal_description="desc", file_path="f.txt",
        )
        assert isinstance(rec, ChangeRecord)
        assert rec in store.get_all()

    def test_jsonl_persistence(self, tmp_path: Path) -> None:
        path = str(tmp_path / "changes.jsonl")
        store1 = ChangeStore(jsonl_path=path)
        store1.record_change(goal_id="g1", goal_description="a", file_path="f1.txt")
        store1.record_change(goal_id="g2", goal_description="b", file_path="f2.txt")

        store2 = ChangeStore(jsonl_path=path)
        assert len(store2.get_all()) == 2
        assert store2.get_all()[0].goal_id == "g1"
        assert store2.get_all()[1].goal_id == "g2"

    def test_jsonl_append_only(self, tmp_path: Path) -> None:
        path = str(tmp_path / "changes.jsonl")
        store = ChangeStore(jsonl_path=path)
        store.record_change(goal_id="g1", goal_description="a", file_path="f1.txt")
        store.record_change(goal_id="g2", goal_description="b", file_path="f2.txt")

        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 2

    def test_jsonl_reload_after_clear(self, tmp_path: Path) -> None:
        path = str(tmp_path / "changes.jsonl")
        store = ChangeStore(jsonl_path=path)
        store.record_change(goal_id="g1", goal_description="a", file_path="f1.txt")
        store.clear()
        assert store.get_all() == []
        assert not os.path.isfile(path)

    def test_jsonl_corrupted_file(self, tmp_path: Path) -> None:
        path = str(tmp_path / "changes.jsonl")
        with open(path, "w") as f:
            f.write("not json\n")

        store = ChangeStore(jsonl_path=path)
        assert store.get_all() == []

    def test_jsonl_empty_file(self, tmp_path: Path) -> None:
        path = str(tmp_path / "changes.jsonl")
        with open(path, "w") as f:
            f.write("")
        store = ChangeStore(jsonl_path=path)
        assert store.get_all() == []

    def test_no_jsonl_path_works(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="a", file_path="f.txt")
        assert len(store.get_all()) == 1


# ============================================================
# ChangeLens Tests
# ============================================================

class TestChangeLens:
    def test_lens_empty(self) -> None:
        lens = ChangeLens(store=ChangeStore())
        assert lens.timeline() == []
        assert lens.component_evolution() == []
        assert lens.goal_evolution() == []

    def test_lens_none_store(self) -> None:
        lens = ChangeLens()
        assert lens.timeline() == []
        assert lens.component_evolution() == []
        assert lens.goal_evolution() == []

    def test_lens_timeline(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="first", file_path="a.txt")
        store.record_change(goal_id="g2", goal_description="second", file_path="b.txt")
        lens = ChangeLens(store=store)
        t = lens.timeline()
        assert len(t) == 2
        assert t[0]["goal_description"] == "second"
        assert t[1]["goal_description"] == "first"

    def test_lens_timeline_count(self) -> None:
        store = ChangeStore()
        for i in range(10):
            store.record_change(goal_id=f"g{i}", goal_description=str(i), file_path=f"f{i}.txt")
        lens = ChangeLens(store=store)
        assert len(lens.timeline(count=3)) == 3

    def test_component_evolution(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="a", file_path="f1.txt", component="Core")
        store.record_change(goal_id="g1", goal_description="a", file_path="f2.txt", component="Core")
        store.record_change(goal_id="g2", goal_description="b", file_path="f3.txt", component="Tests")
        lens = ChangeLens(store=store)
        evo = lens.component_evolution()
        assert len(evo) == 2
        # sorted by total_changes desc
        assert evo[0]["component"] == "Core"
        assert evo[0]["total_changes"] == 2
        assert evo[1]["component"] == "Tests"
        assert evo[1]["total_changes"] == 1

    def test_component_evolution_fields(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="a", file_path="f1.txt", component="Core")
        lens = ChangeLens(store=store)
        evo = lens.component_evolution()
        assert len(evo) == 1
        comp = evo[0]
        assert "component" in comp
        assert "total_changes" in comp
        assert "first_change" in comp
        assert "most_recent" in comp
        assert "action_types" in comp
        assert "goals" in comp

    def test_component_evolution_none_component(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="a", file_path="f1.txt", component=None)
        lens = ChangeLens(store=store)
        evo = lens.component_evolution()
        assert len(evo) == 1
        assert evo[0]["component"] == "(none)"

    def test_component_evolution_goals(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="a", file_path="f1.txt", component="Core")
        store.record_change(goal_id="g2", goal_description="b", file_path="f2.txt", component="Core")
        lens = ChangeLens(store=store)
        evo = lens.component_evolution()
        assert len(evo[0]["goals"]) == 2

    def test_goal_evolution(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="goal one", file_path="f1.txt")
        store.record_change(goal_id="g1", goal_description="goal one", file_path="f2.txt")
        store.record_change(goal_id="g2", goal_description="goal two", file_path="f3.txt")
        lens = ChangeLens(store=store)
        evo = lens.goal_evolution()
        assert len(evo) == 2
        assert evo[0]["goal_id"] == "g1"
        assert evo[0]["change_count"] == 2
        assert evo[1]["change_count"] == 1

    def test_goal_evolution_fields(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="desc", file_path="f1.txt", component="Core")
        lens = ChangeLens(store=store)
        evo = lens.goal_evolution()
        assert len(evo) == 1
        g = evo[0]
        assert g["goal_id"] == "g1"
        assert g["goal_description"] == "desc"
        assert g["files_changed"] == ["f1.txt"]
        assert g["components_changed"] == ["Core"]
        assert len(g["timestamps"]) == 1
        assert g["change_count"] == 1

    def test_goal_evolution_multiple_files(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="desc", file_path="f1.txt")
        store.record_change(goal_id="g1", goal_description="desc", file_path="f2.txt")
        store.record_change(goal_id="g1", goal_description="desc", file_path="f1.txt")
        lens = ChangeLens(store=store)
        evo = lens.goal_evolution()
        assert evo[0]["files_changed"] == ["f1.txt", "f2.txt"]
        assert evo[0]["change_count"] == 3

    def test_deterministic_sorting(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="a", file_path="f1.txt", component="Core")
        store.record_change(goal_id="g2", goal_description="b", file_path="f2.txt", component="Tests")
        lens = ChangeLens(store=store)
        r1 = lens.component_evolution()
        r2 = lens.component_evolution()
        assert r1 == r2

    def test_timeline_empty_when_no_store(self) -> None:
        lens = ChangeLens()
        assert lens.timeline() == []

    def test_component_evolution_empty_when_no_store(self) -> None:
        lens = ChangeLens()
        assert lens.component_evolution() == []

    def test_goal_evolution_empty_when_no_store(self) -> None:
        lens = ChangeLens()
        assert lens.goal_evolution() == []

    def test_action_type_counts_in_component_evolution(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="a", file_path="f1.txt", component="Core", action_type="created")
        store.record_change(goal_id="g1", goal_description="a", file_path="f2.txt", component="Core", action_type="modified")
        store.record_change(goal_id="g1", goal_description="a", file_path="f3.txt", component="Core", action_type="created")
        lens = ChangeLens(store=store)
        evo = lens.component_evolution()
        comp = evo[0]
        assert comp["action_types"]["created"] == 2
        assert comp["action_types"]["modified"] == 1

    def test_action_type_counts_in_goal_evolution(self) -> None:
        store = ChangeStore()
        store.record_change(goal_id="g1", goal_description="a", file_path="f1.txt", action_type="created")
        store.record_change(goal_id="g1", goal_description="a", file_path="f2.txt", action_type="deleted")
        lens = ChangeLens(store=store)
        evo = lens.goal_evolution()
        assert evo[0]["action_types"]["created"] == 1
        assert evo[0]["action_types"]["deleted"] == 1
