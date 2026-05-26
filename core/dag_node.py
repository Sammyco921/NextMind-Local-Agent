# core/dag_node.py
#
# Canonical DAG node and graph definitions (v1.6 planning contract).

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.types import NodeId, ToolName


@dataclass(frozen=True)
class CapabilityManifest:
    """Immutable capability declaration attached at DAG construction time.
    
    Missing manifest = execution failure. Defined here to avoid circular imports.
    """

    dag_id: str
    capabilities: List[Dict[str, Any]] = field(default_factory=list)
    strict_mode: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dag_id": self.dag_id,
            "capabilities": self.capabilities,
            "strict_mode": self.strict_mode,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class DAGNode:
    """
    Immutable DAG node (planning phase only).

    raw_args may contain unresolved artifact references.
    Resolution happens exclusively in ArtifactResolver at execution time.
    """

    node_id: NodeId
    tool_name: ToolName
    raw_args: Dict[str, Any]
    dependencies: List[NodeId] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Roadmap aliases: id / tool
    @property
    def id(self) -> NodeId:
        return self.node_id

    @property
    def tool(self) -> ToolName:
        return self.tool_name

    @property
    def args(self) -> Dict[str, Any]:
        """Backward-compatible alias for raw_args."""
        return self.raw_args


@dataclass(frozen=True)
class DAG:
    nodes: List[DAGNode]
    capability_manifest: Optional[CapabilityManifest] = None
