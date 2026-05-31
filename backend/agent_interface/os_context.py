from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from core.workspace.gateway import WorkspaceFileGateway
from core.workspace.resolver import WorkspaceResolver


class OSContext:
    """Workspace-aware OS integration context.

    Provides deterministic, scoped file operations through
    WorkspaceResolver + WorkspaceFileGateway. Single point of
    configuration for allowed roots and workspace defaults.
    """

    def __init__(
        self,
        project_root: Optional[str] = None,
        default_workspace: Optional[str] = None,
        backend_rel: str = "backend",
    ) -> None:
        self._project_root = (
            os.path.abspath(project_root) if project_root else os.path.abspath(".")
        )
        desktop = os.path.expanduser("~/Desktop/NextMind")
        self._default_ws = (
            os.path.abspath(default_workspace) if default_workspace else desktop
        )
        self._backend_rel = backend_rel
        self._backend_ws = os.path.abspath(
            os.path.join(self._project_root, backend_rel)
        )

        allowed: List[str] = [self._project_root]
        if self._default_ws != self._project_root:
            allowed.append(self._default_ws)
        if self._backend_ws not in allowed:
            allowed.append(self._backend_ws)

        self._resolver = WorkspaceResolver(
            allowed_roots=allowed,
            default_workspace=self._default_ws,
            backend_workspace=self._backend_rel,
        )
        self._gateway = WorkspaceFileGateway(resolver=self._resolver)

    @property
    def default_workspace(self) -> str:
        return self._default_ws

    @property
    def backend_workspace(self) -> str:
        return self._backend_ws

    @property
    def project_root(self) -> str:
        return self._project_root

    @property
    def allowed_roots(self) -> List[str]:
        return list(self._resolver.allowed_roots)

    @property
    def resolver(self) -> WorkspaceResolver:
        return self._resolver

    @property
    def gateway(self) -> WorkspaceFileGateway:
        return self._gateway

    def to_dict(self) -> Dict[str, Any]:
        return {
            "default_workspace": self._default_ws,
            "backend_workspace": self._backend_ws,
            "project_root": self._project_root,
            "allowed_roots": self._resolver.allowed_roots,
        }
