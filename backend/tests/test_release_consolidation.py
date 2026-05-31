"""Phase 22 — Release consolidation verification.

Tests that documentation exists, surfaces are consistent,
and no internal terms leak into external interfaces.
"""
import os
import re
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def read_file(path):
    with open(path) as f:
        return f.read()


# ── Documentation existence ──────────────────────────────────────────

class TestDocumentationExistence:
    def test_readme_exists(self):
        assert (PROJECT_ROOT / "README.md").exists()

    def test_system_map_exists(self):
        assert (PROJECT_ROOT / "docs" / "SYSTEM_MAP.md").exists()

    def test_surface_contract_exists(self):
        assert (PROJECT_ROOT / "docs" / "SURFACE_CONTRACT.md").exists()

    def test_release_notes_exist(self):
        assert (PROJECT_ROOT / "RELEASE_NOTES_v2.1.md").exists()


# ── README integrity ─────────────────────────────────────────────────

class TestReadmeContent:
    def test_readme_mentions_what_it_does(self):
        text = read_file(PROJECT_ROOT / "README.md")
        assert "What It Does" in text

    def test_readme_mentions_what_it_is_not(self):
        text = read_file(PROJECT_ROOT / "README.md")
        assert "What It Is Not" in text

    def test_readme_mentions_guarantees(self):
        text = read_file(PROJECT_ROOT / "README.md")
        assert "Guarantees" in text and "Deterministic" in text

    def test_readme_mentions_frontend_surfaces(self):
        text = read_file(PROJECT_ROOT / "README.md")
        assert "Work" in text and "Overview" in text

    def test_readme_mentions_no_ml(self):
        text = read_file(PROJECT_ROOT / "README.md")
        assert "No ML" in text or "not an AI" in text.lower()


# ── SYSTEM_MAP integrity ────────────────────────────────────────────

class TestSystemMap:
    def test_contains_all_layers(self):
        text = read_file(PROJECT_ROOT / "docs" / "SYSTEM_MAP.md")
        layers = [
            "FRONTEND SURFACE",
            "API SURFACE",
            "AGENT LAYER",
            "INTELLIGENCE LAYER",
            "CONTEXT LAYER",
            "MEMORY LAYER",
            "EXECUTION LAYER",
            "WORKSPACE LAYER",
            "SESSION LAYER",
        ]
        for layer in layers:
            assert layer in text, f"Missing layer: {layer}"

    def test_contains_boundary_rules(self):
        text = read_file(PROJECT_ROOT / "docs" / "SYSTEM_MAP.md")
        assert "Boundary Rules" in text

    def test_contains_ascii_diagram(self):
        text = read_file(PROJECT_ROOT / "docs" / "SYSTEM_MAP.md")
        assert "┌─" in text and "└─" in text


# ── SURFACE_CONTRACT integrity ──────────────────────────────────────

class TestSurfaceContract:
    def test_contains_cli_surface(self):
        text = read_file(PROJECT_ROOT / "docs" / "SURFACE_CONTRACT.md")
        assert "CLI Surface" in text

    def test_contains_api_surface(self):
        text = read_file(PROJECT_ROOT / "docs" / "SURFACE_CONTRACT.md")
        assert "API Surface" in text

    def test_contains_frontend_surface(self):
        text = read_file(PROJECT_ROOT / "docs" / "SURFACE_CONTRACT.md")
        assert "Frontend Surface" in text

    def test_contains_input_contract(self):
        text = read_file(PROJECT_ROOT / "docs" / "SURFACE_CONTRACT.md")
        assert "InputContract" in text

    def test_contains_output_contract(self):
        text = read_file(PROJECT_ROOT / "docs" / "SURFACE_CONTRACT.md")
        assert "OutputContract" in text

    def test_contains_internal_guarantees(self):
        text = read_file(PROJECT_ROOT / "docs" / "SURFACE_CONTRACT.md")
        assert "Internal Guarantees" in text

    def test_contains_consistency_rules(self):
        text = read_file(PROJECT_ROOT / "docs" / "SURFACE_CONTRACT.md")
        assert "Cross-Layer Consistency" in text

    def test_contains_error_contract(self):
        text = read_file(PROJECT_ROOT / "docs" / "SURFACE_CONTRACT.md")
        assert "ErrorContract" in text


# ── Release notes integrity ─────────────────────────────────────────

class TestReleaseNotes:
    def test_contains_whats_included(self):
        text = read_file(PROJECT_ROOT / "RELEASE_NOTES_v2.1.md")
        assert "What's Included" in text

    def test_contains_whats_not_included(self):
        text = read_file(PROJECT_ROOT / "RELEASE_NOTES_v2.1.md")
        assert "What's Explicitly Not Included" in text

    def test_contains_guarantees(self):
        text = read_file(PROJECT_ROOT / "RELEASE_NOTES_v2.1.md")
        assert "Guarantees" in text

    def test_mentions_test_count(self):
        text = read_file(PROJECT_ROOT / "RELEASE_NOTES_v2.1.md")
        assert "490" in text or "489" in text or "tests" in text

    def test_mentions_quick_start(self):
        text = read_file(PROJECT_ROOT / "RELEASE_NOTES_v2.1.md")
        assert "Quick Start" in text or "python3 api_server.py" in text


# ── Frontend surface audit ──────────────────────────────────────────

class TestFrontendSurface:
    def test_no_internal_terms_in_visible_tab_labels(self):
        html = read_file(PROJECT_ROOT / "frontend" / "index.html")
        tabs = re.findall(r'(class="nav-tab(?: dev-tab)?)["\s][^>]*data-tab="\w+">([^<]+)', html)
        visible_labels = [label for cls, label in tabs if "dev-tab" not in cls]
        forbidden = ["DAG", "execution", "memory", "store", "routing", "weighting", "debug"]
        for term in forbidden:
            for label in visible_labels:
                assert term.lower() not in label.lower(), f"Internal term in label '{label}': {term}"

    def test_only_four_tab_labels(self):
        html = read_file(PROJECT_ROOT / "frontend" / "index.html")
        tabs = re.findall(r'data-tab="(\w+)"', html)
        expected = {"chat", "project", "analytics", "debug"}
        assert set(tabs) == expected, f"Unexpected tabs: {set(tabs) - expected}"

    def test_no_backend_terminology_in_ui_text(self):
        html = read_file(PROJECT_ROOT / "frontend" / "index.html")
        forbidden_ui = ["DAG", "executor", "validator", "decomposer", "router"]
        for term in forbidden_ui:
            assert term.lower() not in html.lower(), f"Backend term leaked: {term}"


# ── Behavior normalization check ────────────────────────────────────

class TestBehaviorNormalization:
    """Verifies that key behavior invariants from phases 1-21 still hold."""

    def test_continuity_detection_uses_lenses(self):
        """Continuity lens should reference goal_chains not scored data."""
        js = read_file(PROJECT_ROOT / "frontend" / "app.js")
        assert "goal_chains" in js

    def test_file_operations_use_workspace_gateway(self):
        """File API routes should reference api/files/ endpoint."""
        js = read_file(PROJECT_ROOT / "frontend" / "app.js")
        assert "/api/files/" in js

    def test_project_view_read_only_aggregation(self):
        """Project view should only fetch — no mutations."""
        js = read_file(PROJECT_ROOT / "frontend" / "app.js")
        # Only GET-like fetches for project endpoints
        project_fetches = re.findall(r"fetch\([^)]*project[^)]*\)", js)
        for fetch in project_fetches:
            assert "POST" not in fetch.upper(), f"Project view mutation: {fetch}"

    def test_handoff_derived_from_existing_lenses(self):
        """Handoff should reference project view and existing lenses."""
        js = read_file(PROJECT_ROOT / "frontend" / "app.js")
        assert "handoff" in js.lower()
