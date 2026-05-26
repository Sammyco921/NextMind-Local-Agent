# core/execution_context.py
#
# v1.4: Typed artifact runtime — all artifacts carry ArtifactType metadata.

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.artifact_types import Artifact, ArtifactType
from core.dag_node import DAG
from core.types import NodeId


@dataclass
class ExecutionContext:
    """
    Single source of truth for runtime execution state (v1.6).

    All cross-node data flows through typed artifacts only.
    """

    goal: str
    start_time: float = field(default_factory=time.time)

    dag: Optional[DAG] = None

    # node_id -> typed Artifact (canonical store)
    artifacts: Dict[NodeId, Artifact] = field(default_factory=dict)

    # ordered execution records
    execution_log: List[Dict[str, Any]] = field(default_factory=list)

    # auxiliary runtime flags (no hidden implicit state elsewhere)
    state: Dict[str, Any] = field(default_factory=dict)

    current_step: Optional[NodeId] = None
    step_index: int = 0
    errors: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Artifact access
    # ------------------------------------------------------------------

    def store_artifact(self, node_id: NodeId, result: Artifact) -> None:
        self.artifacts[node_id] = result

    def store_typed(
        self, node_id: NodeId, artifact_type: ArtifactType, value: Any
    ) -> None:
        self.artifacts[node_id] = Artifact(type=artifact_type, value=value)

    def get_artifact(self, node_id: NodeId) -> Artifact:
        if node_id not in self.artifacts:
            raise KeyError(f"No artifact for node: {node_id}")
        return self.artifacts[node_id]

    def has_artifact(self, node_id: NodeId) -> bool:
        return node_id in self.artifacts

    def get_raw(self, node_id: NodeId) -> Any:
        """Return the raw value without Artifact wrapper (for resolver compatibility)."""
        return self.get_artifact(node_id).value

    # Backward-compatible aliases
    def store_output(self, node_id: NodeId, result: Artifact) -> None:
        self.store_artifact(node_id, result)

    def get_output(self, node_id: NodeId) -> Artifact:
        return self.get_artifact(node_id)

    @property
    def outputs(self) -> Dict[NodeId, Artifact]:
        return self.artifacts

    @property
    def trace(self) -> List[Dict[str, Any]]:
        return self.execution_log

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log_execution(
        self,
        node_id: NodeId,
        tool_name: str,
        resolved_args: Dict[str, Any],
        result: Any,
        status: str,
        *,
        artifact_type: str | None = None,
    ) -> None:
        entry: Dict[str, Any] = {
            "node_id": node_id,
            "tool_name": tool_name,
            "args": resolved_args,
            "status": status,
            "result": result,
            "timestamp": time.time(),
        }
        if artifact_type is not None:
            entry["artifact_type"] = artifact_type
        self.execution_log.append(entry)

    def add_step_trace(
        self,
        node_id: NodeId,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        status: str,
    ) -> None:
        self.log_execution(node_id, tool_name, args, result, status)

    def add_error(self, error: str) -> None:
        self.errors.append(error)

    def set_current_step(self, step_id: NodeId) -> None:
        self.current_step = step_id
        self.step_index += 1

    def snapshot(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "elapsed_time": time.time() - self.start_time,
            "current_step": self.current_step,
            "step_index": self.step_index,
            "errors": self.errors,
            "artifacts": list(self.artifacts.keys()),
            "execution_log_length": len(self.execution_log),
            "state": dict(self.state),
        }
