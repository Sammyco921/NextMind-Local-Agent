from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from core.structure.relationship_store import RelationshipRecord, RelationshipStore
from core.structure.relationship_lens import RelationshipLens


# ============================================================
# RelationshipRecord Tests
# ============================================================

class TestRelationshipRecord:
    def test_to_dict_roundtrip(self) -> None:
        rec = RelationshipRecord(
            timestamp="2025-01-01T00:00:00",
            goal_id="g1",
            goal_description="test goal",
            artifacts=["a.py", "b.py"],
            components=["Core", "Tests"],
        )
        d = rec.to_dict()
        restored = RelationshipRecord.from_dict(d)
        assert restored.timestamp == "2025-01-01T00:00:00"
        assert restored.goal_id == "g1"
        assert restored.goal_description == "test goal"
        assert restored.artifacts == ["a.py", "b.py"]
        assert restored.components == ["Core", "Tests"]

    def test_from_dict_missing_fields(self) -> None:
        d: dict = {}
        rec = RelationshipRecord.from_dict(d)
        assert rec.goal_id == ""
        assert rec.artifacts == []
        assert rec.components == []

    def test_artifacts_stored_as_provided(self) -> None:
        rec = RelationshipRecord(
            timestamp="t", goal_id="g1", goal_description="d",
            artifacts=["z.py", "a.py"],
        )
        assert rec.artifacts == ["z.py", "a.py"]


# ============================================================
# RelationshipStore Tests
# ============================================================

class TestRelationshipStore:
    def test_empty_store(self) -> None:
        store = RelationshipStore()
        assert store.get_all() == []
        assert store.get_by_goal("x") == []
        assert store.get_by_artifact("y") == []

    def test_record_relationship(self) -> None:
        store = RelationshipStore()
        rec = store.record_relationship(
            goal_id="g1",
            goal_description="add feature",
            artifacts=["a.py", "b.py"],
            components=["Core"],
        )
        assert rec.goal_id == "g1"
        assert rec.artifacts == ["a.py", "b.py"]
        assert rec.components == ["Core"]
        assert rec.timestamp != ""

    def test_record_relationship_defaults(self) -> None:
        store = RelationshipStore()
        rec = store.record_relationship(goal_id="g1", goal_description="d")
        assert rec.artifacts == []
        assert rec.components == []

    def test_get_by_goal(self) -> None:
        store = RelationshipStore()
        store.record_relationship(goal_id="g1", goal_description="a", artifacts=["f1.py"])
        store.record_relationship(goal_id="g2", goal_description="b", artifacts=["f2.py"])
        store.record_relationship(goal_id="g1", goal_description="c", artifacts=["f3.py"])
        assert len(store.get_by_goal("g1")) == 2
        assert len(store.get_by_goal("g2")) == 1

    def test_get_by_artifact(self) -> None:
        store = RelationshipStore()
        store.record_relationship(goal_id="g1", goal_description="a", artifacts=["f1.py", "f2.py"])
        store.record_relationship(goal_id="g2", goal_description="b", artifacts=["f1.py"])
        assert len(store.get_by_artifact("f1.py")) == 2
        assert len(store.get_by_artifact("f2.py")) == 1
        assert len(store.get_by_artifact("f3.py")) == 0

    def test_get_by_component(self) -> None:
        store = RelationshipStore()
        store.record_relationship(goal_id="g1", goal_description="a", components=["Core"])
        store.record_relationship(goal_id="g2", goal_description="b", components=["Core"])
        store.record_relationship(goal_id="g3", goal_description="c", components=["Tests"])
        assert len(store.get_by_component("Core")) == 2
        assert len(store.get_by_component("Tests")) == 1

    def test_goal_description_truncated(self) -> None:
        store = RelationshipStore()
        long_desc = "x" * 200
        rec = store.record_relationship(goal_id="g1", goal_description=long_desc)
        assert len(rec.goal_description) == 120

    def test_store_clear(self) -> None:
        store = RelationshipStore()
        store.record_relationship(goal_id="g1", goal_description="a", artifacts=["f1.py"])
        assert len(store.get_all()) == 1
        store.clear()
        assert store.get_all() == []

    def test_jsonl_persistence(self, tmp_path: Path) -> None:
        path = str(tmp_path / "relationships.jsonl")
        store1 = RelationshipStore(jsonl_path=path)
        store1.record_relationship(goal_id="g1", goal_description="a", artifacts=["f1.py"])
        store1.record_relationship(goal_id="g2", goal_description="b", artifacts=["f2.py"])

        store2 = RelationshipStore(jsonl_path=path)
        assert len(store2.get_all()) == 2

    def test_jsonl_append_only(self, tmp_path: Path) -> None:
        path = str(tmp_path / "relationships.jsonl")
        store = RelationshipStore(jsonl_path=path)
        store.record_relationship(goal_id="g1", goal_description="a", artifacts=["f1.py"])
        store.record_relationship(goal_id="g2", goal_description="b", artifacts=["f2.py"])
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 2

    def test_jsonl_corrupted_file(self, tmp_path: Path) -> None:
        path = str(tmp_path / "relationships.jsonl")
        with open(path, "w") as f:
            f.write("not json\n")
        store = RelationshipStore(jsonl_path=path)
        assert store.get_all() == []

    def test_no_jsonl_path_works(self) -> None:
        store = RelationshipStore()
        store.record_relationship(goal_id="g1", goal_description="a", artifacts=["f1.py"])
        assert len(store.get_all()) == 1


# ============================================================
# RelationshipLens Tests
# ============================================================

class TestRelationshipLens:
    def test_empty_store(self) -> None:
        lens = RelationshipLens(store=RelationshipStore())
        assert lens.file_relationships() == []
        assert lens.component_relationships() == []
        assert lens.goal_relationships() == []

    def test_none_store(self) -> None:
        lens = RelationshipLens()
        assert lens.file_relationships() == []
        assert lens.component_relationships() == []
        assert lens.goal_relationships() == []

    def test_file_relationships_single_pair(self) -> None:
        store = RelationshipStore()
        store.record_relationship(
            goal_id="g1", goal_description="a",
            artifacts=["a.py", "b.py"],
        )
        lens = RelationshipLens(store=store)
        rels = lens.file_relationships()
        assert len(rels) == 2
        for r in rels:
            if r["file_path"] == "a.py":
                assert len(r["observed_with"]) == 1
                assert r["observed_with"][0]["file_path"] == "b.py"
                assert r["observed_with"][0]["cooccurrence_count"] == 1
            elif r["file_path"] == "b.py":
                assert len(r["observed_with"]) == 1
                assert r["observed_with"][0]["file_path"] == "a.py"

    def test_file_relationships_multiple_occurrences(self) -> None:
        store = RelationshipStore()
        for _ in range(3):
            store.record_relationship(
                goal_id="g1", goal_description="a",
                artifacts=["a.py", "b.py"],
            )
        lens = RelationshipLens(store=store)
        rels = lens.file_relationships()
        for r in rels:
            if r["file_path"] == "a.py":
                assert r["observed_with"][0]["cooccurrence_count"] == 3

    def test_file_relationships_sorted_by_total(self) -> None:
        store = RelationshipStore()
        store.record_relationship(goal_id="g1", goal_description="a", artifacts=["a.py", "b.py"])
        store.record_relationship(goal_id="g2", goal_description="b", artifacts=["a.py", "b.py", "c.py"])
        store.record_relationship(goal_id="g3", goal_description="c", artifacts=["d.py", "e.py"])
        lens = RelationshipLens(store=store)
        rels = lens.file_relationships()
        assert rels[0]["total_cooccurrences"] >= rels[1]["total_cooccurrences"]

    def test_component_relationships(self) -> None:
        store = RelationshipStore()
        store.record_relationship(
            goal_id="g1", goal_description="a",
            artifacts=["f1.py"], components=["Core", "Tests"],
        )
        lens = RelationshipLens(store=store)
        rels = lens.component_relationships()
        assert len(rels) == 2
        for r in rels:
            if r["component"] == "Core":
                assert r["observed_with"][0]["component"] == "Tests"
            elif r["component"] == "Tests":
                assert r["observed_with"][0]["component"] == "Core"

    def test_component_relationships_multiple(self) -> None:
        store = RelationshipStore()
        for _ in range(5):
            store.record_relationship(
                goal_id="g1", goal_description="a",
                artifacts=["f1.py"], components=["Core", "Frontend"],
            )
        lens = RelationshipLens(store=store)
        rels = lens.component_relationships()
        for r in rels:
            assert r["observed_with"][0]["cooccurrence_count"] == 5

    def test_goal_relationships_no_overlap(self) -> None:
        store = RelationshipStore()
        store.record_relationship(goal_id="g1", goal_description="a", artifacts=["a.py"])
        store.record_relationship(goal_id="g2", goal_description="b", artifacts=["b.py"])
        lens = RelationshipLens(store=store)
        assert lens.goal_relationships() == []

    def test_goal_relationships_with_overlap(self) -> None:
        store = RelationshipStore()
        store.record_relationship(goal_id="g1", goal_description="goal one", artifacts=["a.py", "b.py"])
        store.record_relationship(goal_id="g2", goal_description="goal two", artifacts=["a.py", "c.py"])
        lens = RelationshipLens(store=store)
        rels = lens.goal_relationships()
        assert len(rels) == 1
        r = rels[0]
        assert r["shared_files"] == ["a.py"]
        assert r["overlap_count"] == 1

    def test_goal_relationships_component_overlap(self) -> None:
        store = RelationshipStore()
        store.record_relationship(
            goal_id="g1", goal_description="a",
            artifacts=["f1.py"], components=["Core"],
        )
        store.record_relationship(
            goal_id="g2", goal_description="b",
            artifacts=["f2.py"], components=["Core"],
        )
        lens = RelationshipLens(store=store)
        rels = lens.goal_relationships()
        assert len(rels) == 1
        assert rels[0]["shared_components"] == ["Core"]

    def test_goal_relationships_sorted_by_overlap(self) -> None:
        store = RelationshipStore()
        store.record_relationship(goal_id="g1", goal_description="a", artifacts=["a.py", "b.py"])
        store.record_relationship(goal_id="g2", goal_description="b", artifacts=["a.py"])
        store.record_relationship(goal_id="g3", goal_description="c", artifacts=["a.py", "b.py", "c.py"])
        # g1 overlaps with g3 (2 files), g1 with g2 (1 file), g2 with g3 (1 file)
        lens = RelationshipLens(store=store)
        rels = lens.goal_relationships()
        if len(rels) > 1:
            assert rels[0]["overlap_count"] >= rels[1]["overlap_count"]

    def test_deterministic_output(self) -> None:
        store = RelationshipStore()
        store.record_relationship(goal_id="g1", goal_description="a", artifacts=["a.py", "b.py"])
        store.record_relationship(goal_id="g2", goal_description="b", artifacts=["a.py"])
        lens = RelationshipLens(store=store)
        r1 = lens.file_relationships()
        r2 = lens.file_relationships()
        assert r1 == r2

    def test_single_artifact_no_relationship(self) -> None:
        store = RelationshipStore()
        store.record_relationship(goal_id="g1", goal_description="a", artifacts=["a.py"])
        lens = RelationshipLens(store=store)
        assert lens.file_relationships() == []

    def test_single_component_no_relationship(self) -> None:
        store = RelationshipStore()
        store.record_relationship(goal_id="g1", goal_description="a", artifacts=["a.py"], components=["Core"])
        lens = RelationshipLens(store=store)
        assert lens.component_relationships() == []

    def test_relationship_with_both_artifact_and_component_overlap(self) -> None:
        store = RelationshipStore()
        store.record_relationship(
            goal_id="g1", goal_description="a",
            artifacts=["a.py", "b.py"], components=["Core", "Tests"],
        )
        store.record_relationship(
            goal_id="g2", goal_description="b",
            artifacts=["a.py", "c.py"], components=["Core", "Frontend"],
        )
        lens = RelationshipLens(store=store)
        rels = lens.goal_relationships()
        assert len(rels) == 1
        assert rels[0]["overlap_count"] == 2  # 1 shared file + 1 shared component
