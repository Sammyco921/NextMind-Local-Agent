from __future__ import annotations

import os
from typing import List, Optional


class WorkspaceEscapeError(Exception):
    """Raised when a path resolves outside allowed workspace roots."""


class WorkspaceResolver:
    """Deterministic workspace path resolution.

    Normalizes file paths, resolves defaults, prevents escape outside
    allowed roots. Rule-based only — no inference, no guessing, no
    smart relocation.
    """

    def __init__(
        self,
        allowed_roots: Optional[List[str]] = None,
        default_workspace: Optional[str] = None,
        backend_workspace: Optional[str] = None,
    ) -> None:
        self._allowed_roots = [
            os.path.abspath(r) for r in (allowed_roots or [])
        ]
        self._default = (
            os.path.abspath(default_workspace) if default_workspace else None
        )
        self._backend = backend_workspace  # kept relative

    @property
    def default_workspace(self) -> Optional[str]:
        return self._default

    @property
    def backend_workspace(self) -> Optional[str]:
        return self._backend

    @property
    def allowed_roots(self) -> List[str]:
        return list(self._allowed_roots)

    def resolve(
        self,
        path: str,
        context: str = "auto",
    ) -> str:
        if not path or not path.strip():
            raise ValueError("Path must not be empty")

        path = path.strip()

        # 1. Explicit absolute path
        if os.path.isabs(path):
            resolved = os.path.abspath(path)
            self._assert_within_roots(resolved)
            return resolved

        # 2. Contextual resolution
        if context == "backend" or (context == "auto" and path.startswith("./")):
            base = self._find_backend_root()
            resolved = os.path.abspath(os.path.join(base, path))
        else:
            base = self._default
            if base is None:
                base = self._find_project_root()
            resolved = os.path.abspath(os.path.join(base, path))

        self._assert_within_roots(resolved)
        return resolved

    def _assert_within_roots(self, resolved: str) -> None:
        if not self._allowed_roots:
            return
        for root in self._allowed_roots:
            if resolved == root or resolved.startswith(root + os.sep):
                return
        nearest = min(self._allowed_roots, key=lambda r: len(r))
        raise WorkspaceEscapeError(
            f"Path {resolved} is outside allowed workspace roots "
            f"(nearest: {nearest})"
        )

    def _find_project_root(self) -> str:
        candidates = [os.path.abspath("."), os.path.abspath(os.path.dirname("."))]
        for c in candidates:
            if c in self._allowed_roots:
                return c
        if self._allowed_roots:
            return self._allowed_roots[0]
        return os.path.abspath(".")

    def _find_backend_root(self) -> str:
        if self._backend:
            base = self._backend
            if os.path.isabs(base):
                return base
            for root in self._allowed_roots:
                candidate = os.path.abspath(os.path.join(root, base))
                if os.path.isdir(candidate) or os.path.exists(
                    os.path.dirname(candidate)
                ):
                    return candidate
            return os.path.abspath(
                os.path.join(self._allowed_roots[0] if self._allowed_roots else ".", base)
            )
        return self._find_project_root()
