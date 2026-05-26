# core/repair_planner.py
#
# v1.8: incremental DAG repair — patch failing subgraphs only, never replan from scratch.

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from core.agent_types import EvaluationResult
from core.artifact_refs import artifact_ref
from core.dag_node import DAG, DAGNode
from core.transform_semantics import GoalConstraints
from core.types import ExecutionResult


class RepairPlanner:
    """Minimally patch an existing DAG based on evaluation failures."""

    def fix(
        self,
        dag: DAG,
        execution: ExecutionResult,
        evaluation: EvaluationResult,
        *,
        goal: str = "",
    ) -> DAG:
        if evaluation.passed:
            return dag

        constraints = GoalConstraints.from_goal(goal)
        nodes = list(dag.nodes)
        patched_ids: List[str] = []

        for i, node in enumerate(nodes):
            new_node = self._try_patch_node(
                node,
                evaluation,
                constraints,
                execution,
                nodes,
            )
            if new_node is not None:
                nodes[i] = new_node
                patched_ids.append(node.node_id)

        if not patched_ids:
            nodes = self._patch_failed_execution_nodes(nodes, execution, evaluation)

        return DAG(nodes=nodes)

    def _try_patch_node(
        self,
        node: DAGNode,
        evaluation: EvaluationResult,
        constraints: GoalConstraints,
        execution: ExecutionResult,
        all_nodes: List[DAGNode],
    ) -> Optional[DAGNode]:
        content = (node.raw_args or {}).get("content")
        if not isinstance(content, dict):
            return self._patch_missing_read_dependency(node, evaluation, all_nodes)

        transform = content.get("$transform")
        issues_text = " ".join(evaluation.issues).lower()

        if constraints.requires_word_reverse or "word-level" in issues_text:
            if transform in ("combine_reverse", "reverse"):
                return self._patch_to_word_reverse(node, content, constraints)

        if "character-level" in issues_text and transform == "combine_reverse_words":
            return self._patch_to_char_reverse(node, content)

        if "fewer than two" in issues_text and node.tool_name == "write_file":
            return self._ensure_combine_sources(node, all_nodes)

        if "missing output file" in issues_text and node.tool_name == "write_file":
            return self._reassert_write(node)

        return self._patch_missing_read_dependency(node, evaluation, all_nodes)

    def _patch_to_word_reverse(
        self,
        node: DAGNode,
        content: Dict[str, Any],
        constraints: GoalConstraints,
    ) -> DAGNode:
        sources = content.get("$sources") or []
        sep = constraints.combine_separator or " "
        read_deps = list(node.dependencies)

        if not sources and read_deps:
            sources = [artifact_ref(dep_id) for dep_id in read_deps]

        new_content: Dict[str, Any] = {
            "$transform": "combine_reverse_words",
            "$separator": sep,
            "$sources": copy.deepcopy(sources),
        }
        meta = dict(node.metadata)
        meta["repaired_from"] = content.get("$transform", "unknown")
        meta["repair"] = "word_level_reverse"

        new_args = dict(node.raw_args)
        new_args["content"] = new_content

        return DAGNode(
            node_id=node.node_id,
            tool_name=node.tool_name,
            raw_args=new_args,
            dependencies=read_deps,
            metadata=meta,
        )

    @staticmethod
    def _patch_to_char_reverse(node: DAGNode, content: Dict[str, Any]) -> DAGNode:
        new_content = {
            "$transform": "combine_reverse",
            "$sources": copy.deepcopy(content.get("$sources", [])),
        }
        meta = dict(node.metadata)
        meta["repaired_from"] = content.get("$transform")
        meta["repair"] = "char_level_reverse"
        new_args = dict(node.raw_args)
        new_args["content"] = new_content
        return DAGNode(
            node_id=node.node_id,
            tool_name=node.tool_name,
            raw_args=new_args,
            dependencies=list(node.dependencies),
            metadata=meta,
        )

    @staticmethod
    def _ensure_combine_sources(
        node: DAGNode,
        all_nodes: List[DAGNode],
    ) -> Optional[DAGNode]:
        read_ids = [n.node_id for n in all_nodes if n.tool_name == "read_file"]
        if len(read_ids) < 2:
            return None
        content = (node.raw_args or {}).get("content")
        if not isinstance(content, dict):
            return None
        new_content = dict(content)
        new_content["$sources"] = [artifact_ref(rid) for rid in read_ids[:2]]
        new_args = dict(node.raw_args)
        new_args["content"] = new_content
        meta = dict(node.metadata)
        meta["repair"] = "wire_read_sources"
        return DAGNode(
            node_id=node.node_id,
            tool_name=node.tool_name,
            raw_args=new_args,
            dependencies=read_ids[:2],
            metadata=meta,
        )

    @staticmethod
    def _reassert_write(node: DAGNode) -> DAGNode:
        meta = dict(node.metadata)
        meta["repair"] = "reassert_write"
        return DAGNode(
            node_id=node.node_id,
            tool_name=node.tool_name,
            raw_args=dict(node.raw_args),
            dependencies=list(node.dependencies),
            metadata=meta,
        )

    @staticmethod
    def _patch_missing_read_dependency(
        node: DAGNode,
        evaluation: EvaluationResult,
        all_nodes: List[DAGNode],
    ) -> Optional[DAGNode]:
        if node.tool_name != "read_file":
            return None
        if not any("no prior write" in i.lower() for i in evaluation.issues):
            return None
        filename = (node.raw_args or {}).get("filename")
        if not isinstance(filename, str):
            return None
        writer = next(
            (
                n
                for n in all_nodes
                if n.tool_name == "write_file"
                and (n.raw_args or {}).get("filename") == filename
            ),
            None,
        )
        if writer is None:
            return None
        deps = sorted(set(list(node.dependencies) + [writer.node_id]))
        meta = dict(node.metadata)
        meta["repair"] = "add_write_dependency"
        return DAGNode(
            node_id=node.node_id,
            tool_name=node.tool_name,
            raw_args=dict(node.raw_args),
            dependencies=deps,
            metadata=meta,
        )

    @staticmethod
    def _patch_failed_execution_nodes(
        nodes: List[DAGNode],
        execution: ExecutionResult,
        evaluation: EvaluationResult,
    ) -> List[DAGNode]:
        """Re-queue failed nodes by clearing error metadata (minimal noop patch)."""
        failed_ids = {
            t.get("id")
            for t in execution.trace
            if t.get("status") != "success"
        }
        if not failed_ids:
            return nodes

        updated: List[DAGNode] = []
        for node in nodes:
            if node.node_id in failed_ids:
                meta = dict(node.metadata)
                meta["repair"] = "retry_failed_node"
                meta["evaluation_issues"] = evaluation.issues[:3]
                updated.append(
                    DAGNode(
                        node_id=node.node_id,
                        tool_name=node.tool_name,
                        raw_args=dict(node.raw_args),
                        dependencies=list(node.dependencies),
                        metadata=meta,
                    )
                )
            else:
                updated.append(node)
        return updated
