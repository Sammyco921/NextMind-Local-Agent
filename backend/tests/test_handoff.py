from __future__ import annotations

from typing import Any, Dict

import pytest

from core.handoff import HandoffBuilder, HandoffPackage
from core.memory.project_view import ProjectIntelligenceView


class FakeProjectView:
    """Minimal ProjectIntelligenceView-compatible stub."""

    def overview(self) -> Dict[str, Any]:
        return {
            "active_goals": [{"goal_id": "g1", "description": "do something", "status": "active"}],
            "blocked_goals": [],
            "completed_goals": [],
            "goal_count": {"active": 1, "blocked": 0, "completed": 0, "total": 1},
            "continuation_links": [],
            "recurring_failures": [],
            "repeated_attempts": [],
        }

    def history(self) -> Dict[str, Any]:
        return {
            "entries": [
                {
                    "type": "decision",
                    "description": "tool choice",
                    "detail": "write_file",
                    "rationale": "needed to create a file",
                    "timestamp": "2025-01-01T00:00:00",
                },
            ],
        }

    def changes(self) -> Dict[str, Any]:
        return {
            "timeline": [],
        }

    def structure(self) -> Dict[str, Any]:
        return {
            "file_count": 10,
            "directory_count": 3,
            "components": [
                {"name": "Core", "file_count": 5, "directory_count": 1},
                {"name": "Tests", "file_count": 3, "directory_count": 1},
            ],
        }

    def relationships(self) -> Dict[str, Any]:
        return {
            "file_relationships": [],
            "component_relationships": [],
            "goal_relationships": [],
        }


class TestHandoffPackage:
    def test_to_dict_includes_handoff_mode(self) -> None:
        pkg = HandoffPackage({"project_summary": {}}, mode="brief")
        d = pkg.to_dict()
        assert d["handoff_mode"] == "brief"
        assert "generated_at" in d

    def test_to_dict_includes_data(self) -> None:
        pkg = HandoffPackage({"project_summary": {"key": "val"}}, mode="standard")
        d = pkg.to_dict()
        assert d["project_summary"]["key"] == "val"

    def test_invalid_mode_defaults_to_standard(self) -> None:
        pkg = HandoffPackage({}, mode="invalid")
        assert pkg.mode == "standard"

    def test_property_mode(self) -> None:
        pkg = HandoffPackage({}, mode="brief")
        assert pkg.mode == "brief"
        pkg2 = HandoffPackage({}, mode="comprehensive")
        assert pkg2.mode == "comprehensive"

    def test_to_markdown_contains_sections(self) -> None:
        pkg = HandoffPackage({
            "project_summary": {
                "goal_count": {"total": 5, "active": 2, "blocked": 1, "completed": 2},
            },
            "current_focus": {
                "salient_goals": [{"description": "do thing", "status": "active"}],
                "continuation_chains": [],
                "blockers": [],
            },
            "recurring_issues": {
                "recurring_failures": [],
                "repeated_attempts": [],
            },
        }, mode="standard")
        md = pkg.to_markdown()
        assert "# Project Handoff (standard)" in md
        assert "## Project Summary" in md
        assert "Total goals: 5" in md
        assert "Active: 2" in md

    def test_to_markdown_empty_package(self) -> None:
        pkg = HandoffPackage({}, mode="brief")
        md = pkg.to_markdown()
        assert "# Project Handoff (brief)" in md
        assert "## Project Summary" not in md

    def test_to_markdown_decisions(self) -> None:
        pkg = HandoffPackage({
            "project_summary": {"goal_count": {}},
            "current_focus": {},
            "recent_decisions": [
                {"decision_point": "tool choice", "selected": "write_file", "rationale": "needed"},
            ],
            "recurring_issues": {},
        }, mode="standard")
        md = pkg.to_markdown()
        assert "## Recent Decisions" in md
        assert "tool choice" in md

    def test_to_markdown_activity(self) -> None:
        pkg = HandoffPackage({
            "project_summary": {"goal_count": {}},
            "current_focus": {},
            "recurring_issues": {},
            "recent_activity": {
                "recent_changes": [
                    {"action_type": "modified", "file_path": "src/main.py"},
                ],
            },
        }, mode="standard")
        md = pkg.to_markdown()
        assert "## Recent Activity" in md
        assert "modified src/main.py" in md

    def test_to_markdown_structure(self) -> None:
        pkg = HandoffPackage({
            "project_summary": {"goal_count": {}},
            "current_focus": {},
            "recurring_issues": {},
            "project_structure": {
                "file_count": 10,
                "directory_count": 3,
                "components": [{"name": "Core", "file_count": 5}],
            },
        }, mode="comprehensive")
        md = pkg.to_markdown()
        assert "## Project Structure" in md
        assert "Files: 10" in md
        assert "Core: 5 files" in md

    def test_to_markdown_relationships(self) -> None:
        pkg = HandoffPackage({
            "project_summary": {"goal_count": {}},
            "current_focus": {},
            "recurring_issues": {},
            "relationships": {
                "file_relationships": [
                    {"file_path": "a.py", "observed_with": [{"file_path": "b.py", "cooccurrence_count": 3}]},
                ],
                "component_relationships": [
                    {"component": "Core", "observed_with": [{"component": "Tests", "cooccurrence_count": 5}]},
                ],
            },
        }, mode="standard")
        md = pkg.to_markdown()
        assert "## Observed Relationships" in md
        assert "a.py often with b.py (3x)" in md
        assert "Core often with Tests (5x)" in md

    def test_to_markdown_issues(self) -> None:
        pkg = HandoffPackage({
            "project_summary": {"goal_count": {}},
            "current_focus": {},
            "recurring_issues": {
                "recurring_failures": [{"error": "timeout", "count": 3}],
                "repeated_attempts": [{"description": "retry", "attempt_count": 5}],
            },
        }, mode="standard")
        md = pkg.to_markdown()
        assert "## Recurring Issues" in md
        assert "timeout (x3)" in md
        assert "retry (x5)" in md


class TestHandoffBuilder:
    def test_builder_none_view(self) -> None:
        builder = HandoffBuilder()
        pkg = builder.build(mode="standard")
        assert isinstance(pkg, HandoffPackage)
        assert pkg.mode == "standard"

    def test_builder_with_fake_view(self) -> None:
        pv = FakeProjectView()
        builder = HandoffBuilder(project_view=pv)
        pkg = builder.build(mode="standard")
        d = pkg.to_dict()
        assert d["handoff_mode"] == "standard"
        assert "project_summary" in d
        assert "current_focus" in d

    def test_builder_brief(self) -> None:
        pv = FakeProjectView()
        builder = HandoffBuilder(project_view=pv)
        pkg = builder.build(mode="brief")
        d = pkg.to_dict()
        assert d["handoff_mode"] == "brief"
        assert "project_summary" in d
        assert "current_focus" in d
        assert "recent_decisions" not in d
        assert "relationships" not in d

    def test_builder_standard_includes_recent_decisions(self) -> None:
        pv = FakeProjectView()
        builder = HandoffBuilder(project_view=pv)
        pkg = builder.build(mode="standard")
        d = pkg.to_dict()
        assert "recent_decisions" in d
        assert "recent_activity" in d
        assert "relationships" in d
        assert "project_structure" not in d

    def test_builder_comprehensive_includes_all(self) -> None:
        pv = FakeProjectView()
        builder = HandoffBuilder(project_view=pv)
        pkg = builder.build(mode="comprehensive")
        d = pkg.to_dict()
        assert "recent_decisions" in d
        assert "recent_activity" in d
        assert "relationships" in d
        assert "project_structure" in d
        assert "recurring_issues" in d

    def test_builder_issues_always_present(self) -> None:
        pv = FakeProjectView()
        builder = HandoffBuilder(project_view=pv)
        for mode in ("brief", "standard", "comprehensive"):
            pkg = builder.build(mode=mode)
            d = pkg.to_dict()
            assert "recurring_issues" in d

    def test_builder_invalid_mode_defaults(self) -> None:
        pv = FakeProjectView()
        builder = HandoffBuilder(project_view=pv)
        pkg = builder.build(mode="invalid")
        assert pkg.mode == "standard"

    def test_builder_deterministic(self) -> None:
        pv = FakeProjectView()
        builder = HandoffBuilder(project_view=pv)
        pkg1 = builder.build(mode="standard").to_dict()
        pkg2 = builder.build(mode="standard").to_dict()
        del pkg1["generated_at"]
        del pkg2["generated_at"]
        assert pkg1 == pkg2

    def test_builder_no_view_returns_empty(self) -> None:
        builder = HandoffBuilder()
        pkg = builder.build(mode="comprehensive").to_dict()
        assert pkg == {
            "handoff_mode": "comprehensive",
            "generated_at": pkg["generated_at"],
        }
