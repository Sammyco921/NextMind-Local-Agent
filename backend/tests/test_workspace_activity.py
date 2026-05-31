from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from core.workspace.activity_lens import WorkspaceActivityLens
from core.workspace.activity_tracker import (
    WorkspaceActivityRecord,
    WorkspaceActivityTracker,
)


class TestWorkspaceActivityRecord:
    def test_to_dict(self) -> None:
        rec = WorkspaceActivityRecord(
            path="src/main.py",
            filename="main.py",
            extension=".py",
            size=100,
            modified_at="2025-01-01T00:00:00",
            workspace_type="project",
        )
        d = rec.to_dict()
        assert d["path"] == "src/main.py"
        assert d["filename"] == "main.py"
        assert d["extension"] == ".py"
        assert d["size"] == 100
        assert d["modified_at"] == "2025-01-01T00:00:00"
        assert d["workspace_type"] == "project"
        assert "observed_at" in d

    def test_to_dict_auto_observed_at(self) -> None:
        rec = WorkspaceActivityRecord(
            path="f.txt", filename="f.txt", extension=".txt",
            size=0, modified_at="2025-01-01T00:00:00",
        )
        d = rec.to_dict()
        assert d["observed_at"] != ""


class TestWorkspaceActivityTracker:
    def test_empty_directory(self, tmp_path: Path) -> None:
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        records = tracker.scan()
        assert records == []

    def test_single_file(self, tmp_path: Path) -> None:
        (tmp_path / "hello.txt").write_text("hello")
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        records = tracker.scan()
        assert len(records) == 1
        assert records[0].filename == "hello.txt"
        assert records[0].extension == ".txt"
        assert records[0].path == "hello.txt"

    def test_multiple_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.js").write_text("b")
        (tmp_path / "c.txt").write_text("c")
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        records = tracker.scan()
        assert len(records) == 3

    def test_subdirectories(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "nested.py").write_text("nested")
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        records = tracker.scan()
        assert len(records) == 1
        assert records[0].filename == "nested.py"
        assert records[0].path == os.path.join("sub", "nested.py")

    def test_excluded_dirs(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("config")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "c.py").write_text("c")
        (tmp_path / "real.py").write_text("real")
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        records = tracker.scan()
        assert len(records) == 1
        assert records[0].filename == "real.py"

    def test_hidden_files_excluded(self, tmp_path: Path) -> None:
        (tmp_path / ".hidden.py").write_text("hidden")
        (tmp_path / "visible.py").write_text("visible")
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        records = tracker.scan()
        assert len(records) == 1
        assert records[0].filename == "visible.py"

    def test_deterministic_sort(self, tmp_path: Path) -> None:
        (tmp_path / "z.py").write_text("z")
        time.sleep(0.01)
        (tmp_path / "a.py").write_text("a")
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        records = tracker.scan()
        # newest first
        assert records[0].filename == "a.py"
        assert records[1].filename == "z.py"

    def test_max_depth(self, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)
        (deep / "f.txt").write_text("deep")
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)], max_depth=3)
        records = tracker.scan()
        assert len(records) == 0

    def test_extension_detection(self, tmp_path: Path) -> None:
        (tmp_path / "file.py").write_text("py")
        (tmp_path / "file.js").write_text("js")
        (tmp_path / "file").write_text("noext")
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        records = tracker.scan()
        exts = {r.filename: r.extension for r in records}
        assert exts["file.py"] == ".py"
        assert exts["file.js"] == ".js"
        assert exts["file"] == ""

    def test_multiple_roots(self, tmp_path: Path) -> None:
        r1 = tmp_path / "root1"
        r2 = tmp_path / "root2"
        r1.mkdir()
        r2.mkdir()
        (r1 / "a.txt").write_text("a")
        (r2 / "b.txt").write_text("b")
        tracker = WorkspaceActivityTracker(
            roots=[str(r1), str(r2)]
        )
        records = tracker.scan()
        assert len(records) == 2

    def test_nonexistent_root(self) -> None:
        tracker = WorkspaceActivityTracker(roots=["/nonexistent/path"])
        records = tracker.scan()
        assert records == []

    def test_read_only_no_mutation(self, tmp_path: Path) -> None:
        (tmp_path / "f.txt").write_text("original")
        before = (tmp_path / "f.txt").read_text()
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        tracker.scan()
        after = (tmp_path / "f.txt").read_text()
        assert before == after


class TestWorkspaceActivityLens:
    def test_lens_empty(self, tmp_path: Path) -> None:
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        lens = WorkspaceActivityLens(tracker=tracker)
        assert lens.recent_activity() == []
        assert lens.active_files() == []
        summary = lens.workspace_summary()
        assert summary["total_files"] == 0

    def test_lens_none_tracker(self) -> None:
        lens = WorkspaceActivityLens()
        assert lens.recent_activity() == []
        assert lens.active_files() == []
        assert lens.workspace_summary()["total_files"] == 0

    def test_recent_activity_filter(self, tmp_path: Path) -> None:
        (tmp_path / "old.txt").write_text("old")
        time.sleep(0.1)
        (tmp_path / "new.txt").write_text("new")
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        lens = WorkspaceActivityLens(tracker=tracker)
        recent = lens.recent_activity(hours=24)
        assert len(recent) == 2

    def test_active_files_limit(self, tmp_path: Path) -> None:
        for i in range(5):
            (tmp_path / f"f{i}.txt").write_text(str(i))
            time.sleep(0.01)
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        lens = WorkspaceActivityLens(tracker=tracker)
        assert len(lens.active_files(limit=3)) == 3
        assert len(lens.active_files(limit=10)) == 5

    def test_workspace_summary_counts(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.py").write_text("b")
        (tmp_path / "c.js").write_text("c")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "d.txt").write_text("d")
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        lens = WorkspaceActivityLens(tracker=tracker)
        summary = lens.workspace_summary()
        assert summary["total_files"] == 4
        assert summary["directory_count"] == 1  # sub/

    def test_extension_breakdown(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.py").write_text("b")
        (tmp_path / "c.js").write_text("c")
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        lens = WorkspaceActivityLens(tracker=tracker)
        ext = lens.workspace_summary()["extension_breakdown"]
        assert ext[".py"] == 2
        assert ext[".js"] == 1

    def test_deterministic_output(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.py").write_text("b")
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        lens = WorkspaceActivityLens(tracker=tracker)
        r1 = lens.workspace_summary()
        r2 = lens.workspace_summary()
        assert r1 == r2

    def test_recent_activity_simple(self, tmp_path: Path) -> None:
        (tmp_path / "f.py").write_text("f")
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        lens = WorkspaceActivityLens(tracker=tracker)
        simple = lens.recent_activity_simple(hours=24)
        assert len(simple) == 1
        assert "filename" in simple[0]
        assert "path" in simple[0]
        assert "modified_at" in simple[0]
        assert "content" not in simple[0]

    def test_recent_activity_simple_limit(self, tmp_path: Path) -> None:
        for i in range(5):
            (tmp_path / f"f{i}.txt").write_text(str(i))
            time.sleep(0.01)
        tracker = WorkspaceActivityTracker(roots=[str(tmp_path)])
        lens = WorkspaceActivityLens(tracker=tracker)
        assert len(lens.recent_activity_simple(limit=2)) == 2
