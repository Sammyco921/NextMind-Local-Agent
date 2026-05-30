from __future__ import annotations

from typing import Any, Dict, Optional

from core.artifact_resolver import ArtifactResolver
from core.artifact_types import Artifact, ArtifactType
from core.dag_node import DAG, DAGNode
from core.dag_topology import topological_order
from core.execution_context import ExecutionContext
from core.memory.event_builder import build_event
from core.memory.execution_memory_store import ExecutionMemoryStore
from core.tool_contracts import get_contract, has_contract
from core.tool_registry import ToolRegistry
from core.types import ExecutionResult, NodeId


class DAGExecutor:
    def __init__(
        self,
        registry: ToolRegistry,
        execution_memory: ExecutionMemoryStore | None = None,
    ) -> None:
        self.registry = registry
        self.resolver = ArtifactResolver()
        self._memory = execution_memory

    def _emit(self, dag_id: str, goal_id: str, node: DAGNode, status: str, **extra) -> None:
        if self._memory is None:
            return
        try:
            event = build_event(
                dag_id=dag_id,
                goal_id=goal_id,
                node_id=node.node_id,
                tool=node.tool_name,
                args=dict(node.raw_args),
                status=status,
                **extra,
            )
            self._memory.append_event(event)
        except Exception:
            pass

    def execute(self, dag: DAG, goal: str) -> ExecutionResult:
        context = ExecutionContext(goal=goal, dag=dag)
        dag_id = dag.dag_id or goal
        status = "success"
        all_nodes = list(topological_order(dag.nodes))

        for node in all_nodes:
            context.set_current_step(node.node_id)
            self._emit(dag_id, goal, node, "running")

            try:
                resolved_args = self.resolver.resolve_inputs(node, context)
                output = self.registry.run(node.tool_name, resolved_args)
                artifact = self._wrap_in_artifact(node, output)
                context.store_artifact(node.node_id, artifact)
                context.log_execution(
                    node.node_id, node.tool_name, resolved_args, output, "success",
                    artifact_type=artifact.type.value,
                )
                self._emit(dag_id, goal, node, "success", output=output)
            except Exception as e:
                error_msg = str(e)
                context.add_error(error_msg)
                context.log_execution(
                    node.node_id, node.tool_name, dict(node.raw_args),
                    {"error": error_msg}, "failed",
                )
                self._emit(dag_id, goal, node, "failed", error=error_msg)
                status = "failed"
                break

        if status == "failed":
            for skipped in all_nodes[len(context.execution_log):]:
                self._emit(dag_id, goal, skipped, "skipped")

        trace = [
            {
                "id": entry["node_id"],
                "tool": entry["tool_name"],
                "args": entry["args"],
                "status": "success" if entry["status"] == "success" else "fail",
                "result": entry["result"],
                "artifact_type": entry.get("artifact_type"),
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
        if has_contract(node.tool_name):
            contract = get_contract(node.tool_name)
            return Artifact(type=contract.output_type, value=output)
        return Artifact(type=ArtifactType.NULL, value=output)
