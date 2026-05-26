# core/dag_executor.py
#
# v1.4: Typed artifact execution — preserves ArtifactType metadata through entire runtime.

from __future__ import annotations

from typing import Any, Dict, List

from core.artifact_resolver import ArtifactResolver
from core.artifact_types import Artifact, ArtifactType
from core.dag_node import DAG, DAGNode
from core.dag_topology import topological_order
from core.errors import UnresolvedDependencyError
from core.execution_context import ExecutionContext
from core.tool_contracts import get_contract, has_contract
from core.tool_registry import ToolRegistry
from core.types import ExecutionResult, NodeId


class DAGExecutor:
    """Executes a DAG in strict topological order with typed artifact flow."""

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
                artifact = self._wrap_in_artifact(node, output)
                context.store_artifact(node.node_id, artifact)
                context.log_execution(
                    node.node_id,
                    node.tool_name,
                    resolved_args,
                    output,
                    "success",
                    artifact_type=artifact.type.value,
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
                "artifact_type": entry.get("artifact_type"),
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

    @staticmethod
    def _wrap_in_artifact(node: DAGNode, output: Any) -> Artifact:
        """Wrap raw tool output in typed Artifact based on tool contract."""
        if has_contract(node.tool_name):
            contract = get_contract(node.tool_name)
            return Artifact(type=contract.output_type, value=output)
        return Artifact(type=ArtifactType.NULL, value=output)

