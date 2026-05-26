# core/dag_topology.py
#
# Shared deterministic DAG topological ordering (v1.2).

from __future__ import annotations

from collections import deque
from typing import Dict, List

from core.dag_node import DAGNode
from core.types import NodeId


def topological_order(nodes: List[DAGNode]) -> List[DAGNode]:
    """Deterministic topological order; raises ValueError on cycle or bad deps."""
    by_id = {n.node_id: n for n in nodes}
    in_degree = {n.node_id: 0 for n in nodes}
    adj: Dict[NodeId, List[NodeId]] = {n.node_id: [] for n in nodes}

    for node in nodes:
        for dep in node.dependencies:
            if dep not in by_id:
                raise ValueError(
                    f"Node {node.node_id} depends on unknown node: {dep}"
                )
            adj[dep].append(node.node_id)
            in_degree[node.node_id] += 1

    queue = deque(sorted(nid for nid, deg in in_degree.items() if deg == 0))
    ordered: List[DAGNode] = []

    while queue:
        nid = queue.popleft()
        ordered.append(by_id[nid])
        for child in sorted(adj[nid]):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    if len(ordered) != len(nodes):
        raise ValueError("DAG contains a cycle")

    return ordered
