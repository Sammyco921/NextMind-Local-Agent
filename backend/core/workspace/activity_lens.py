from __future__ import annotations

import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from core.workspace.activity_tracker import WorkspaceActivityRecord, WorkspaceActivityTracker


class WorkspaceActivityLens:
    """Deterministic read models over workspace filesystem state.

    Pure observation — no scoring, no persistence, no inference.
    """

    def __init__(self, tracker: WorkspaceActivityTracker | None = None) -> None:
        self._tracker = tracker

    def _records(self) -> List[WorkspaceActivityRecord]:
        if self._tracker is None:
            return []
        return self._tracker.scan()

    def recent_activity(self, hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        results: List[Dict[str, Any]] = []
        for r in self._records():
            try:
                mtime = datetime.fromisoformat(r.modified_at)
                if mtime >= cutoff:
                    results.append(r.to_dict())
            except (ValueError, TypeError):
                continue
        return results[:limit]

    def active_files(self, limit: int = 20) -> List[Dict[str, Any]]:
        records = self._records()
        return [r.to_dict() for r in records[:limit]]

    def workspace_summary(self) -> Dict[str, Any]:
        records = self._records()
        ext_counts: Counter = Counter()
        dirs: set = set()
        recently_modified = 0
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        for r in records:
            ext_counts[r.extension or "(none)"] += 1
            parent = os.path.dirname(r.path) if r.path else "."
            if parent:
                dirs.add(parent)
            try:
                mtime = datetime.fromisoformat(r.modified_at)
                if mtime >= cutoff:
                    recently_modified += 1
            except (ValueError, TypeError):
                pass

        return {
            "total_files": len(records),
            "directory_count": len(dirs),
            "extension_breakdown": dict(ext_counts.most_common()),
            "recently_modified_24h": recently_modified,
        }

    def recent_activity_simple(self, hours: int = 24, limit: int = 10) -> List[Dict[str, Any]]:
        return [
            {
                "path": r["path"],
                "filename": r["filename"],
                "modified_at": r["modified_at"],
                "extension": r.get("extension", ""),
            }
            for r in self.recent_activity(hours=hours, limit=limit)
        ]
