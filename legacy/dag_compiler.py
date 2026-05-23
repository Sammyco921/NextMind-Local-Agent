from typing import Any, Dict, List

from core.dag import DAG, DAGNode
from tools.tool_registry import ToolRegistry


class DAGCompiler:
    """
    v1 DAG Compiler

    Responsibilities:
    - Normalize planner output into valid DAG
    - Validate tool existence early
    - Prevent malformed execution graphs
    """

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    # =====================================================
    # ENTRY POINT
    # =====================================================

    def compile(self, raw_dag: Any) -> DAG:

        dag = self._ensure_dag(raw_dag)

        self._validate_tools(dag)
        self._normalize_nodes(dag)

        return dag

    # =====================================================
    # DAG NORMALIZATION
    # =====================================================

    def _ensure_dag(self, raw: Any) -> DAG:

        # If already DAG → return
        if isinstance(raw, DAG):
            return raw

        # If dict-style DAG → convert
        if isinstance(raw, dict):

            nodes = raw.get("nodes", {})
            edges = raw.get("edges", {})

            dag = DAG()

            for node_id, node_data in nodes.items():

                dag.add_node(
                    DAGNode(
                        node_id=node_id,
                        tool=node_data["tool"],
                        args=node_data.get("args", {}),
                        depends_on=node_data.get("depends_on", []),
                        status="pending",
                    )
                )

            return dag

        raise ValueError(f"Invalid DAG format: {type(raw)}")

    # =====================================================
    # TOOL VALIDATION (CRITICAL)
    # =====================================================

    def _validate_tools(self, dag: DAG):

        for node in dag.nodes.values():

            if not self.registry.has(node.tool):
                raise ValueError(f"unknown_tool: {node.tool}")

    # =====================================================
    # NORMALIZATION PASS
    # =====================================================

    def _normalize_nodes(self, dag: DAG):

        for node in dag.nodes.values():

            # ensure args always dict
            if node.args is None:
                node.args = {}

            if not isinstance(node.args, dict):
                raise ValueError(
                    f"Node {node.node_id}: args must be dict"
                )

            # ensure depends_on always list
            if node.depends_on is None:
                node.depends_on = []

            if not isinstance(node.depends_on, list):
                raise ValueError(
                    f"Node {node.node_id}: depends_on must be list"
                )