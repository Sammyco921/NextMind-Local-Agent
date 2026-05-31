from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from core.workspace.resolver import WorkspaceResolver


class WorkspaceFileGateway:
    """Mechanical file operations scoped to a defined workspace.

    Pure abstraction over OS file I/O — no interpretation, no
    restructuring, no smart relocation. All paths are resolved
    through WorkspaceResolver before touching the filesystem.
    """

    def __init__(self, resolver: WorkspaceResolver) -> None:
        self._resolver = resolver

    @property
    def resolver(self) -> WorkspaceResolver:
        return self._resolver

    def create(self, path: str, content: str, context: str = "auto") -> Dict[str, Any]:
        resolved = self._resolver.resolve(path, context=context)
        parent = os.path.dirname(resolved)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
        return {
            "status": "success",
            "file": resolved,
            "bytes": len(content),
            "action": "created",
        }

    def read(self, path: str, context: str = "auto") -> Dict[str, Any]:
        resolved = self._resolver.resolve(path, context=context)
        if not os.path.isfile(resolved):
            raise FileNotFoundError(f"File not found: {resolved}")
        with open(resolved, "r", encoding="utf-8") as f:
            content = f.read()
        return {
            "status": "success",
            "file": resolved,
            "content": content,
            "bytes": len(content),
            "action": "read",
        }

    def update(self, path: str, content: str, context: str = "auto") -> Dict[str, Any]:
        resolved = self._resolver.resolve(path, context=context)
        if not os.path.isfile(resolved):
            raise FileNotFoundError(f"File not found: {resolved}")
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
        return {
            "status": "success",
            "file": resolved,
            "bytes": len(content),
            "action": "updated",
        }

    def list_dir(self, path: str = ".", context: str = "auto") -> Dict[str, Any]:
        resolved = self._resolver.resolve(path, context=context)
        if not os.path.isdir(resolved):
            raise FileNotFoundError(f"Directory not found: {resolved}")
        items = sorted(os.listdir(resolved))
        return {
            "status": "success",
            "path": resolved,
            "items": items,
            "count": len(items),
            "action": "listed",
        }

    def delete(self, path: str, context: str = "auto") -> Dict[str, Any]:
        resolved = self._resolver.resolve(path, context=context)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"Path not found: {resolved}")
        if os.path.isfile(resolved):
            os.remove(resolved)
        elif os.path.isdir(resolved):
            os.rmdir(resolved)
        return {
            "status": "success",
            "file": resolved,
            "action": "deleted",
        }
