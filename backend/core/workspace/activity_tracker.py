from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


_EXCLUDED_DIRS = frozenset({
    ".git", "__pycache__", ".pytest_cache", "node_modules",
    ".DS_Store", ".opencode", ".eggs", "egg-info", ".tox",
    ".mypy_cache", ".ruff_cache",
})


@dataclass
class WorkspaceActivityRecord:
    path: str
    filename: str
    extension: str
    size: int
    modified_at: str
    workspace_type: str = "project"
    observed_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "filename": self.filename,
            "extension": self.extension,
            "size": self.size,
            "modified_at": self.modified_at,
            "workspace_type": self.workspace_type,
            "observed_at": self.observed_at or datetime.now(timezone.utc).isoformat(),
        }


class WorkspaceActivityTracker:
    """Deterministic, read-only workspace scanner.

    Scans root directories, collects metadata (path, size, timestamp,
    extension). No file content reading, no caching, no persistence.

    Same filesystem state → same output (deterministic sort).
    """

    def __init__(
        self,
        roots: Optional[List[str]] = None,
        max_depth: int = 4,
    ) -> None:
        self._roots = [os.path.abspath(r) for r in (roots or [])]
        self._max_depth = max_depth

    def scan(self) -> List[WorkspaceActivityRecord]:
        results: List[WorkspaceActivityRecord] = []
        for root in self._roots:
            if not os.path.isdir(root):
                continue
            self._scan_directory(root, root, 0, results)
        results.sort(key=lambda r: (r.modified_at, r.path), reverse=True)
        return results

    def _scan_directory(
        self,
        root: str,
        current: str,
        depth: int,
        results: List[WorkspaceActivityRecord],
    ) -> None:
        if depth > self._max_depth:
            return
        try:
            names = sorted(os.listdir(current))
        except (OSError, PermissionError):
            return

        for name in names:
            full = os.path.join(current, name)
            rel = os.path.relpath(full, root)
            if name.startswith(".") or name in _EXCLUDED_DIRS:
                continue
            if os.path.isdir(full):
                self._scan_directory(root, full, depth + 1, results)
            elif os.path.isfile(full):
                try:
                    stat = os.stat(full)
                    ext = os.path.splitext(name)[1].lower()
                    mtime = datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat()
                    results.append(WorkspaceActivityRecord(
                        path=rel,
                        filename=name,
                        extension=ext,
                        size=stat.st_size,
                        modified_at=mtime,
                    ))
                except (OSError, PermissionError):
                    pass
