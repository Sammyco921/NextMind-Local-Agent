import json
import re
import os
import sys
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


def read_index_html():
    path = FRONTEND_DIR / "index.html"
    assert path.exists(), f"index.html not found at {path}"
    return path.read_text()


def read_app_js():
    path = FRONTEND_DIR / "app.js"
    assert path.exists(), f"app.js not found at {path}"
    return path.read_text()


class TestSurfaces:
    def test_three_surfaces_exist(self):
        html = read_index_html()
        assert 'data-tab="chat"' in html
        assert 'data-tab="project"' in html
    def test_work_surface_label(self):
        html = read_index_html()
        assert re.search(r'data-tab="chat"[^>]*>Work<', html)
    def test_overview_surface_label(self):
        html = read_index_html()
        assert re.search(r'data-tab="project"[^>]*>Overview<', html)
    def test_system_surfaces_hidden_by_default(self):
        html = read_index_html()
        assert 'class="nav-tab dev-tab"' in html
        assert 'data-tab="analytics"' in html
        assert 'data-tab="debug"' in html


class TestSystemHidden:
    def test_insights_has_dev_tab_class(self):
        html = read_index_html()
        assert re.search(r'class="nav-tab dev-tab"[^>]*data-tab="analytics"', html)
    def test_debug_has_dev_tab_class(self):
        html = read_index_html()
        assert re.search(r'class="nav-tab dev-tab"[^>]*data-tab="debug"', html)
    def test_dev_toggle_exists(self):
        html = read_index_html()
        assert 'id="dev-toggle"' in html


class TestWorkspaceDropdown:
    def test_workspace_is_single_dropdown(self):
        html = read_index_html()
        assert '<select id="ws-selector">' in html
    def test_no_workspace_name_span(self):
        html = read_index_html()
        assert 'id="ws-name"' not in html
    def test_default_option_present(self):
        html = read_index_html()
        assert '<option value="default">default</option>' in html


class TestCommandGrouping:
    def test_cmd_groups_defined(self):
        js = read_app_js()
        assert "Work" in js
        assert "Navigation" in js
        assert "System" in js
        assert "Advanced" in js
    def test_work_commands_listed(self):
        js = read_app_js()
        assert "'create file'" in js
        assert "'read file'" in js
    def test_system_commands_listed(self):
        js = read_app_js()
        assert "'generate handoff'" in js
    def test_advanced_commands_listed(self):
        js = read_app_js()
        assert "'switch workspace'" in js
        assert "'create workspace'" in js
    def test_cmd_suggestions_element_created(self):
        js = read_app_js()
        assert "cmdSuggestions" in js
        assert "cmd-group-header" in js


class TestProjectViewDefaultLens:
    def test_overview_is_default_and_active(self):
        html = read_index_html()
        assert re.search(r'class="lens-btn active"[^>]*data-lens="overview"', html)
    def test_other_lenses_collapsed(self):
        html = read_index_html()
        assert 'id="lens-more" class="hidden"' in html
    def test_expand_button_exists(self):
        html = read_index_html()
        assert 'id="lens-expand-btn"' in html
    def test_history_lens_label(self):
        html = read_index_html()
        assert "History" in html
    def test_continuity_lens_label(self):
        html = read_index_html()
        assert "Continue Work" in html
    def test_structure_lens_label(self):
        html = read_index_html()
        assert "Layout" in html
    def test_relationships_lens_label(self):
        html = read_index_html()
        assert "Connections" in html


class TestHandoffDefaultMode:
    def test_handoff_fetches_standard_mode(self):
        js = read_app_js()
        assert "mode=standard" in js
    def test_handoff_details_hidden_by_default(self):
        js = read_app_js()
        assert "handoff-details" in js
    def test_handoff_toggle_button_created(self):
        js = read_app_js()
        assert "handoff-toggle" in js
        assert "More details" in js


class TestSystemInvariant:
    def test_system_invariant_comment_present(self):
        html = read_index_html()
        assert "understandable in under 10 seconds" in html
        assert "hidden, nested" in html
