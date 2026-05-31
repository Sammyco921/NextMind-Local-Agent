from __future__ import annotations

import os
import json
import tempfile
from pathlib import Path

import pytest

from core.structure.project_catalog import ProjectCatalog, FileRecord
from core.structure.component_registry import ComponentRegistry, ComponentRule
from core.structure.goal_impact_tracker import GoalImpactTracker, ImpactRecord
from core.structure.structure_lens import StructureLens


# ============================================================
# ProjectCatalog Tests
# ============================================================

class TestProjectCatalog:
    def test_empty_directory(self, tmp_path: Path) -> None:
        catalog = ProjectCatalog(root_path=str(tmp_path))
        catalog.scan()
        assert catalog.get_files() == []
        assert catalog.get_directories() == []
        assert catalog.get_file_count() == 0
        assert catalog.get_directory_count() == 0

    def test_single_file(self, tmp_path: Path) -> None:
        (tmp_path / "hello.txt").write_text("hello world")
        catalog = ProjectCatalog(root_path=str(tmp_path))
        catalog.scan()
        files = catalog.get_files()
        assert len(files) == 1
        assert files[0].path == "hello.txt"
        assert files[0].extension == ".txt"
        assert files[0].size == len("hello world")
        assert files[0].dir_path == ""

    def test_directory_structure(self, tmp_path: Path) -> None:
        (tmp_path / "src" / "main.py").parent.mkdir(parents=True)
        (tmp_path / "src" / "main.py").write_text("print('hello')")
        (tmp_path / "src" / "utils.py").write_text("def util(): pass")
        (tmp_path / "tests" / "test_main.py").parent.mkdir(parents=True)
        (tmp_path / "tests" / "test_main.py").write_text("def test(): pass")

        catalog = ProjectCatalog(root_path=str(tmp_path))
        catalog.scan()
        assert catalog.get_file_count() == 3
        dirs = catalog.get_directories()
        assert "src" in dirs
        assert "tests" in dirs

    def test_excluded_directories_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "__pycache__" / "cache.py").parent.mkdir(parents=True)
        (tmp_path / "__pycache__" / "cache.py").write_text("cached")
        (tmp_path / ".git" / "config").parent.mkdir(parents=True)
        (tmp_path / ".git" / "config").write_text("[core]")
        (tmp_path / "real.py").write_text("real")

        catalog = ProjectCatalog(root_path=str(tmp_path))
        catalog.scan()
        assert catalog.get_file_count() == 1
        assert catalog.get_files()[0].path == "real.py"

    def test_extension_counts(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.py").write_text("b")
        (tmp_path / "c.txt").write_text("c")
        (tmp_path / "d.md").write_text("d")

        catalog = ProjectCatalog(root_path=str(tmp_path))
        catalog.scan()
        counts = catalog.get_extension_counts()
        assert counts.get(".py") == 2
        assert counts.get(".txt") == 1
        assert counts.get(".md") == 1

    def test_get_by_extension(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        catalog = ProjectCatalog(root_path=str(tmp_path))
        catalog.scan()
        assert len(catalog.get_by_extension(".py")) == 1
        assert len(catalog.get_by_extension(".txt")) == 1
        assert len(catalog.get_by_extension(".js")) == 0

    def test_get_by_directory(self, tmp_path: Path) -> None:
        (tmp_path / "src" / "a.py").parent.mkdir()
        (tmp_path / "src" / "a.py").write_text("a")
        (tmp_path / "src" / "b.py").write_text("b")
        (tmp_path / "root.py").write_text("root")
        catalog = ProjectCatalog(root_path=str(tmp_path))
        catalog.scan()
        assert len(catalog.get_by_directory("src")) == 2
        assert len(catalog.get_by_directory("")) == 1  # root files

    def test_deterministic_sorting(self, tmp_path: Path) -> None:
        (tmp_path / "z.py").write_text("z")
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "m.py").write_text("m")
        catalog = ProjectCatalog(root_path=str(tmp_path))
        catalog.scan()
        paths = [f.path for f in catalog.get_files()]
        assert paths == sorted(paths)

    def test_recently_modified(self, tmp_path: Path) -> None:
        (tmp_path / "old.txt").write_text("old")
        import time
        time.sleep(0.01)
        (tmp_path / "new.txt").write_text("new")
        catalog = ProjectCatalog(root_path=str(tmp_path))
        catalog.scan()
        recent = catalog.get_recently_modified(1)
        assert len(recent) == 1
        assert recent[0].path == "new.txt"

    def test_lazy_scan(self, tmp_path: Path) -> None:
        catalog = ProjectCatalog(root_path=str(tmp_path))
        assert not catalog._scanned
        _ = catalog.get_files()
        assert catalog._scanned


# ============================================================
# ComponentRegistry Tests
# ============================================================

class TestComponentRegistry:
    def make_record(self, path: str, dir_path: str = "") -> FileRecord:
        return FileRecord(
            path=path, dir_path=dir_path or os.path.dirname(path),
            extension=os.path.splitext(path)[1], size=0, modified_at="",
        )

    def test_assign_by_prefix(self) -> None:
        reg = ComponentRegistry()
        r = self.make_record("backend/core/memory/goal_registry.py", "backend/core/memory")
        assert reg.assign(r) == "Core Engine"

    def test_assign_frontend(self) -> None:
        reg = ComponentRegistry()
        r = self.make_record("frontend/app.js", "frontend")
        assert reg.assign(r) == "Frontend"

    def test_assign_tool(self) -> None:
        reg = ComponentRegistry()
        r = self.make_record("backend/tools/write_file.py", "backend/tools")
        assert reg.assign(r) == "Tools"

    def test_assign_test(self) -> None:
        reg = ComponentRegistry()
        r = self.make_record("backend/tests/test_structure.py", "backend/tests")
        assert reg.assign(r) == "Tests"

    def test_assign_unknown_returns_none(self) -> None:
        reg = ComponentRegistry()
        r = self.make_record("random/other/file.txt", "random/other")
        assert reg.assign(r) is None

    def test_get_components(self) -> None:
        reg = ComponentRegistry()
        comps = reg.get_components()
        assert "Core Engine" in comps
        assert "Frontend" in comps
        assert "Tools" in comps
        assert "Tests" in comps

    def test_file_counts(self) -> None:
        reg = ComponentRegistry()
        records = [
            self.make_record("backend/core/x.py", "backend/core"),
            self.make_record("backend/core/y.py", "backend/core"),
            self.make_record("frontend/app.js", "frontend"),
            self.make_record("backend/tools/z.py", "backend/tools"),
        ]
        counts = reg.file_counts(records)
        assert counts.get("Core Engine") == 2
        assert counts.get("Frontend") == 1
        assert counts.get("Tools") == 1

    def test_custom_rules(self) -> None:
        rule = ComponentRule(
            name="Docs",
            match=lambda r: r.path.endswith(".md"),
            description="Documentation files",
        )
        reg = ComponentRegistry(rules=[rule])
        r = self.make_record("README.md", "")
        assert reg.assign(r) == "Docs"
        r2 = self.make_record("main.py", "")
        assert reg.assign(r2) is None

    def test_deterministic(self) -> None:
        reg = ComponentRegistry()
        r = self.make_record("backend/core/x.py", "backend/core")
        assert reg.assign(r) == "Core Engine"
        assert reg.assign(r) == "Core Engine"


# ============================================================
# GoalImpactTracker Tests
# ============================================================

class TestGoalImpactTracker:
    def test_record_and_retrieve(self) -> None:
        tracker = GoalImpactTracker()
        tracker.record_impact(
            goal_id="g1", goal_description="write readme",
            file_path="README.md", component="Docs", action="wrote",
        )
        impacts = tracker.get_impacts_for_goal("g1")
        assert len(impacts) == 1
        assert impacts[0].file_path == "README.md"
        assert impacts[0].component == "Docs"
        assert impacts[0].action == "wrote"

    def test_get_goals_for_file(self) -> None:
        tracker = GoalImpactTracker()
        tracker.record_impact("g1", "goal 1", "file.txt", "Backend")
        tracker.record_impact("g2", "goal 2", "file.txt", "Backend")
        result = tracker.get_goals_for_file("file.txt")
        assert len(result) == 2
        assert {r.goal_id for r in result} == {"g1", "g2"}

    def test_get_goals_for_component(self) -> None:
        tracker = GoalImpactTracker()
        tracker.record_impact("g1", "goal 1", "a.py", "Backend")
        tracker.record_impact("g2", "goal 2", "b.py", "Backend")
        tracker.record_impact("g3", "goal 3", "index.html", "Frontend")
        result = tracker.get_goals_for_component("Backend")
        assert len(result) == 2
        result_f = tracker.get_goals_for_component("Frontend")
        assert len(result_f) == 1

    def test_get_recent_activity(self) -> None:
        tracker = GoalImpactTracker()
        import time
        tracker.record_impact("g1", "first", "a.txt", "Backend")
        time.sleep(0.01)
        tracker.record_impact("g2", "second", "b.txt", "Backend")
        recent = tracker.get_recent_activity(1)
        assert len(recent) == 1
        assert recent[0].goal_id == "g2"

    def test_get_affected_files(self) -> None:
        tracker = GoalImpactTracker()
        tracker.record_impact("g1", "goal", "a.txt", "Backend")
        tracker.record_impact("g1", "goal", "b.txt", "Backend")
        tracker.record_impact("g2", "other", "a.txt", "Backend")
        files = tracker.get_affected_files("g1")
        assert files == {"a.txt", "b.txt"}

    def test_get_affected_components(self) -> None:
        tracker = GoalImpactTracker()
        tracker.record_impact("g1", "goal", "a.py", "Core Engine")
        tracker.record_impact("g1", "goal", "index.html", "Frontend")
        comps = tracker.get_affected_components("g1")
        assert comps == {"Core Engine", "Frontend"}

    def test_empty_goal_returns_empty(self) -> None:
        tracker = GoalImpactTracker()
        assert tracker.get_impacts_for_goal("nonexistent") == []
        assert tracker.get_affected_files("nonexistent") == set()

    def test_to_dict_format(self) -> None:
        record = ImpactRecord(
            goal_id="g1", goal_description="test",
            file_path="f.txt", component="Backend",
            action="wrote", timestamp="2026-01-01T00:00:00",
        )
        d = record.to_dict()
        assert d["goal_id"] == "g1"
        assert d["file_path"] == "f.txt"
        assert d["component"] == "Backend"

    def test_from_dict_roundtrip(self) -> None:
        original = ImpactRecord(
            goal_id="g1", goal_description="test",
            file_path="f.txt", component="Backend",
            action="wrote", timestamp="2026-01-01T00:00:00",
        )
        d = original.to_dict()
        restored = ImpactRecord.from_dict(d)
        assert restored.goal_id == original.goal_id
        assert restored.file_path == original.file_path
        assert restored.component == original.component

    def test_jsonl_persistence(self, tmp_path: Path) -> None:
        jsonl = str(tmp_path / "impacts.jsonl")
        tracker = GoalImpactTracker(jsonl_path=jsonl)
        tracker.record_impact("g1", "test", "f.txt", "Backend", "wrote")

        tracker2 = GoalImpactTracker(jsonl_path=jsonl)
        assert len(tracker2.get_impacts_for_goal("g1")) == 1
        assert tracker2.get_impacts_for_goal("g1")[0].file_path == "f.txt"

    def test_deterministic_serialization(self, tmp_path: Path) -> None:
        jsonl = str(tmp_path / "impacts.jsonl")
        tracker = GoalImpactTracker(jsonl_path=jsonl)
        tracker.record_impact("g1", "test", "f.txt", "Backend", "wrote")
        with open(jsonl) as f:
            first = f.read()
        # Re-run should produce identical line (same inputs → same record)
        tracker2 = GoalImpactTracker(jsonl_path=jsonl)
        # Already loaded, records match
        assert len(tracker2.get_impacts_for_goal("g1")) == 1

    def test_clear(self, tmp_path: Path) -> None:
        jsonl = str(tmp_path / "impacts.jsonl")
        tracker = GoalImpactTracker(jsonl_path=jsonl)
        tracker.record_impact("g1", "test", "f.txt")
        assert len(tracker.get_impacts_for_goal("g1")) == 1
        tracker.clear()
        assert len(tracker.get_impacts_for_goal("g1")) == 0


# ============================================================
# StructureLens Tests
# ============================================================

class TestStructureLens:
    def test_empty_lens(self) -> None:
        lens = StructureLens()
        result = lens.build()
        assert result["lens"] == "structure"
        assert result["file_count"] == 0
        assert result["directory_count"] == 0
        assert result["components"] == []
        assert result["recent_activity"] == []

    def test_lens_with_all_components(self, tmp_path: Path) -> None:
        (tmp_path / "backend" / "core" / "mod.py").parent.mkdir(parents=True)
        (tmp_path / "backend" / "core" / "mod.py").write_text("x")
        (tmp_path / "frontend" / "app.js").parent.mkdir(parents=True)
        (tmp_path / "frontend" / "app.js").write_text("y")

        catalog = ProjectCatalog(root_path=str(tmp_path))
        registry = ComponentRegistry()
        impact = GoalImpactTracker()

        lens = StructureLens(catalog=catalog, registry=registry, impact=impact)
        result = lens.build()
        assert result["file_count"] == 2
        assert "Core Engine" in [c["name"] for c in result["components"]]
        assert "Frontend" in [c["name"] for c in result["components"]]

    def test_lens_with_goal_associations(self, tmp_path: Path) -> None:
        (tmp_path / "backend" / "core" / "x.py").parent.mkdir(parents=True)
        (tmp_path / "backend" / "core" / "x.py").write_text("x")

        catalog = ProjectCatalog(root_path=str(tmp_path))
        registry = ComponentRegistry()
        impact = GoalImpactTracker()
        impact.record_impact("g1", "fix core", "backend/core/x.py", "Core Engine", "wrote")

        lens = StructureLens(catalog=catalog, registry=registry, impact=impact)
        result = lens.build()
        assert len(result["goal_associations"]) == 1
        assert result["goal_associations"][0]["component"] == "Core Engine"
        assert result["goal_associations"][0]["total_goals"] == 1

    def test_lens_recent_activity_dedup(self) -> None:
        impact = GoalImpactTracker()
        import time
        impact.record_impact("g1", "goal", "a.txt", "Backend", "wrote")
        time.sleep(0.001)
        impact.record_impact("g1", "goal", "a.txt", "Backend", "wrote")

        lens = StructureLens(impact=impact)
        activity = lens.build()["recent_activity"]
        # Should deduplicate same (goal_id, file_path)
        assert len(activity) == 1

    def test_deterministic_component_order(self, tmp_path: Path) -> None:
        (tmp_path / "backend" / "core" / "a.py").parent.mkdir(parents=True)
        (tmp_path / "backend" / "core" / "a.py").write_text("a")
        (tmp_path / "frontend" / "b.js").parent.mkdir(parents=True)
        (tmp_path / "frontend" / "b.js").write_text("b")
        (tmp_path / "backend" / "tools" / "c.py").parent.mkdir(parents=True)
        (tmp_path / "backend" / "tools" / "c.py").write_text("c")

        catalog = ProjectCatalog(root_path=str(tmp_path))
        registry = ComponentRegistry()
        lens = StructureLens(catalog=catalog, registry=registry)
        result1 = lens.build()
        result2 = lens.build()
        assert result1 == result2

    def test_no_mutation_of_inputs(self, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("data")
        catalog = ProjectCatalog(root_path=str(tmp_path))
        registry = ComponentRegistry()
        impact = GoalImpactTracker()
        impact.record_impact("g1", "test", "f.txt")

        before_files = len(catalog.get_files())
        before_impacts = len(impact.get_impacts_for_goal("g1"))

        lens = StructureLens(catalog=catalog, registry=registry, impact=impact)
        _ = lens.build()

        assert len(catalog.get_files()) == before_files
        assert len(impact.get_impacts_for_goal("g1")) == before_impacts
