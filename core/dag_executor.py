# core/dag_executor.py
#
# Phase 3: topological execution with ArtifactResolver binding.

from __future__ import annotations

from typing import Any, Dict, List

from core.artifact_resolver import ArtifactResolver
from core.dag_node import DAG, DAGNode
from core.dag_topology import topological_order
from core.errors import UnresolvedDependencyError
from core.execution_context import ExecutionContext
from core.tool_registry import ToolRegistry
from core.types import ExecutionResult, NodeId


class DAGExecutor:
    """Executes a DAG in strict topological order with full artifact resolution."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self.resolver = ArtifactResolver()

    def execute(self, dag: DAG, goal: str) -> ExecutionResult:
        context = ExecutionContext(goal=goal, dag=dag)
        status = "success"

        for node in topological_order(dag.nodes):
            context.set_current_step(node.node_id)

            try:
                resolved_args = self.resolver.resolve_inputs(node, context)
            except UnresolvedDependencyError as e:
                status = "partial_failure"
                context.add_error(str(e))
                context.log_execution(
                    node.node_id,
                    node.tool_name,
                    dict(node.raw_args),
                    {"error": str(e)},
                    "failed",
                )
                break

            try:
                output = self.registry.run(node.tool_name, resolved_args)
                context.store_artifact(node.node_id, output)
                context.log_execution(
                    node.node_id,
                    node.tool_name,
                    resolved_args,
                    output,
                    "success",
                )
            except Exception as e:
                status = "partial_failure"
                context.add_error(str(e))
                context.log_execution(
                    node.node_id,
                    node.tool_name,
                    resolved_args,
                    {"error": str(e)},
                    "failed",
                )
                break

        trace = [
            {
                "id": entry["node_id"],
                "tool": entry["tool_name"],
                "args": entry["args"],
                "status": "success" if entry["status"] == "success" else "fail",
                "result": entry["result"],
                "note": None,
            }
            for entry in context.execution_log
        ]

        return ExecutionResult(
            goal=goal,
            status=status,
            trace=trace,
            steps_executed=len(trace),
        )

