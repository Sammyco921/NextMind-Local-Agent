# core/types.py
#
# NextMind v1.6 — Shared pipeline types (single source of truth)

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, TypedDict

# =====================================================
# PRIMITIVE ALIASES
# =====================================================

NodeId = str
ToolName = str

NodeState = Literal["pending", "running", "success", "failed"]

# Marker for executor-time resolution from dependency outputs
ArgRef = Dict[str, Any]

# =====================================================
# DAG STRUCTURE TYPING
# =====================================================

class NodeDict(TypedDict, total=False):
    node_id: NodeId
    tool_name: ToolName
    raw_args: Dict[str, Any]
    args: Dict[str, Any]
    dependencies: List[NodeId]
    metadata: Dict[str, Any]


class EdgeDict(TypedDict):
    from_node: NodeId
    to_node: NodeId


# =====================================================
# EXECUTION TRACE / RESULT
# =====================================================

class StepTraceEntry(TypedDict, total=False):
    node_id: NodeId
    tool_name: ToolName
    args: Dict[str, Any]
    status: NodeState
    result: Dict[str, Any]
    note: Optional[str]


class ExecutionResultDict(TypedDict, total=False):
    goal: str
    status: str
    steps_executed: int
    trace: List[StepTraceEntry]


# =====================================================
# EXECUTION RESULT (runtime object contract)
# =====================================================

@dataclass
class ExecutionResult:
    goal: str
    status: str
    trace: List[Dict[str, Any]]
    steps_executed: int = 0
    def __post_init__(self) -> None:
        if self.steps_executed == 0:
            self.steps_executed = len(self.trace)

    def to_dict(self) -> ExecutionResultDict:
        return {
            "goal": self.goal,
            "status": self.status,
            "steps_executed": self.steps_executed,
            "trace": self.trace,
        }
