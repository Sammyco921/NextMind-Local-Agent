from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.memory.project_view import ProjectIntelligenceView


HANDOFF_MODES = frozenset({"brief", "standard", "comprehensive"})


class HandoffPackage:
    """Deterministic, portable, read-only project handoff snapshot.

    Synthesizes existing intelligence into a single package.
    No new inference, no new stores, no execution influence.
    """

    def __init__(self, data: Dict[str, Any], mode: str = "standard") -> None:
        self._data = data
        self._mode = mode if mode in HANDOFF_MODES else "standard"

    @property
    def mode(self) -> str:
        return self._mode

    def to_dict(self) -> Dict[str, Any]:
        return {
            "handoff_mode": self._mode,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **self._data,
        }

    def to_markdown(self) -> str:
        lines: List[str] = []
        lines.append(f"# Project Handoff ({self._mode})")
        lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
        lines.append("")

        summary = self._data.get("project_summary", {})
        if summary:
            lines.append("## Project Summary")
            gc = summary.get("goal_count", {})
            lines.append(f"- Total goals: {gc.get('total', 0)}")
            lines.append(f"- Active: {gc.get('active', 0)}")
            lines.append(f"- Blocked: {gc.get('blocked', 0)}")
            lines.append(f"- Completed: {gc.get('completed', 0)}")
            lines.append("")

        focus = self._data.get("current_focus", {})
        if focus:
            lines.append("## Current Focus")
            for g in focus.get("salient_goals", []):
                desc = g.get("description", "?")
                status = g.get("status", "?")
                lines.append(f"- {desc} ({status})")
            for c in focus.get("continuation_chains", []):
                parent = c.get("parent_description", "?")
                child = c.get("child_description", "?")
                lines.append(f"- Continuation: {parent} -> {child}")
            for b in focus.get("blockers", []):
                reason = b.get("reason", "?")
                lines.append(f"- Blocked: {b.get('goal_id', '?')} — {reason}")
            lines.append("")

        decisions = self._data.get("recent_decisions", [])
        if decisions:
            lines.append("## Recent Decisions")
            for d in decisions:
                lines.append(f"- {d.get('decision_point', '?')}: {d.get('selected', '?')}")
                if d.get("rationale"):
                    lines.append(f"  Rationale: {d['rationale']}")
            lines.append("")

        activity = self._data.get("recent_activity", {})
        if activity:
            lines.append("## Recent Activity")
            for c in activity.get("recent_changes", []):
                lines.append(f"- {c.get('action_type', '?')} {c.get('file_path', '?')}")
            lines.append("")

        structure = self._data.get("project_structure", {})
        if structure:
            lines.append("## Project Structure")
            lines.append(f"- Files: {structure.get('file_count', 0)}")
            lines.append(f"- Directories: {structure.get('directory_count', 0)}")
            for comp in structure.get("components", []):
                lines.append(f"- {comp.get('name', '?')}: {comp.get('file_count', 0)} files")
            lines.append("")

        rels = self._data.get("relationships", {})
        if rels:
            lines.append("## Observed Relationships")
            for fr in rels.get("file_relationships", [])[:5]:
                peers = fr.get("observed_with", [])
                if peers:
                    top = peers[0]
                    lines.append(f"- {fr['file_path']} often with {top['file_path']} ({top['cooccurrence_count']}x)")
            for cr in rels.get("component_relationships", [])[:5]:
                peers = cr.get("observed_with", [])
                if peers:
                    top = peers[0]
                    lines.append(f"- {cr['component']} often with {top['component']} ({top['cooccurrence_count']}x)")
            lines.append("")

        issues = self._data.get("recurring_issues", {})
        if issues:
            lines.append("## Recurring Issues")
            for f in issues.get("recurring_failures", []):
                lines.append(f"- Error: {f.get('error', '?')} (x{f.get('count', 0)})")
            for a in issues.get("repeated_attempts", []):
                lines.append(f"- Repeated: {a.get('description', '?')} (x{a.get('attempt_count', 0)})")
            lines.append("")

        return "\n".join(lines)


class HandoffBuilder:
    """Composes existing projections into a HandoffPackage.

    Pure composition — no inference, no new scoring, no execution influence.
    """

    def __init__(self, project_view: ProjectIntelligenceView | None = None) -> None:
        self._pv = project_view

    def build(self, mode: str = "standard") -> HandoffPackage:
        if mode not in HANDOFF_MODES:
            mode = "standard"
        data: Dict[str, Any] = {}

        if self._pv is None:
            return HandoffPackage(data, mode=mode)

        data["project_summary"] = self._build_project_summary()
        data["current_focus"] = self._build_current_focus()

        if mode in ("standard", "comprehensive"):
            data["recent_decisions"] = self._build_recent_decisions()
            data["recent_activity"] = self._build_recent_activity()
            data["relationships"] = self._build_relationships()

        if mode == "comprehensive":
            data["project_structure"] = self._build_project_structure()

        data["recurring_issues"] = self._build_recurring_issues()

        return HandoffPackage(data, mode=mode)

    def _build_project_summary(self) -> Dict[str, Any]:
        overview = self._pv.overview()
        return {
            "goal_count": overview.get("goal_count", {}),
            "active_goals": [
                {"description": g.get("description", ""), "status": "active"}
                for g in overview.get("active_goals", [])
            ],
            "blocked_goals": [
                {"description": g.get("description", ""), "reason": g.get("reason", "")}
                for g in overview.get("blocked_goals", [])
            ],
            "completed_goals": [
                {"description": g.get("description", "")}
                for g in overview.get("completed_goals", [])
            ],
        }

    def _build_current_focus(self) -> Dict[str, Any]:
        overview = self._pv.overview()
        salient = []
        for g in overview.get("active_goals", []):
            salient.append({
                "goal_id": g.get("goal_id", ""),
                "description": g.get("description", ""),
                "status": "active",
            })
        for g in overview.get("blocked_goals", []):
            salient.append({
                "goal_id": g.get("goal_id", ""),
                "description": g.get("description", ""),
                "status": "blocked",
            })
        return {
            "salient_goals": salient[:5],
            "continuation_chains": overview.get("continuation_links", [])[:3],
            "blockers": overview.get("blocked_goals", [])[:5],
        }

    def _build_recent_decisions(self) -> List[Dict[str, Any]]:
        history = self._pv.history()
        decisions = [
            e for e in history.get("entries", []) if e.get("type") == "decision"
        ]
        return [
            {
                "decision_point": d.get("description", ""),
                "selected": d.get("detail", ""),
                "rationale": d.get("rationale", ""),
                "timestamp": d.get("timestamp", ""),
            }
            for d in decisions[-10:]
        ]

    def _build_recent_activity(self) -> Dict[str, Any]:
        changes = self._pv.changes()
        return {
            "recent_changes": changes.get("timeline", [])[:10],
        }

    def _build_project_structure(self) -> Dict[str, Any]:
        structure = self._pv.structure()
        return {
            "file_count": structure.get("file_count", 0),
            "directory_count": structure.get("directory_count", 0),
            "components": [
                {
                    "name": c.get("name", ""),
                    "file_count": c.get("file_count", 0),
                }
                for c in structure.get("components", [])
            ],
        }

    def _build_relationships(self) -> Dict[str, Any]:
        rels = self._pv.relationships()
        return {
            "file_relationships": [
                {
                    "file_path": r.get("file_path", ""),
                    "observed_with": [
                        {"file_path": p.get("file_path", ""), "cooccurrence_count": p.get("cooccurrence_count", 0)}
                        for p in (r.get("observed_with") or [])[:3]
                    ],
                }
                for r in (rels.get("file_relationships") or [])[:10]
            ],
            "component_relationships": [
                {
                    "component": r.get("component", ""),
                    "observed_with": [
                        {"component": p.get("component", ""), "cooccurrence_count": p.get("cooccurrence_count", 0)}
                        for p in (r.get("observed_with") or [])[:3]
                    ],
                }
                for r in (rels.get("component_relationships") or [])[:10]
            ],
        }

    def _build_recurring_issues(self) -> Dict[str, Any]:
        overview = self._pv.overview()
        return {
            "recurring_failures": overview.get("recurring_failures", [])[:10],
            "repeated_attempts": overview.get("repeated_attempts", [])[:10],
        }
