from typing import List, Any, Optional


# =====================================================
# DAG NODE
# =====================================================

class DAGNode:
    """
    Single executable unit in the DAG.
    """

    def __init__(
        self,
        node_id: str,
        tool: str,
        args: dict,
        depends_on: Optional[List[str]] = None
    ):
        self.node_id = node_id
        self.tool = tool
        self.args = args or {}
        self.depends_on = depends_on or []

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "tool": self.tool,
            "args": self.args,
            "depends_on": self.depends_on
        }


# =====================================================
# DAG CONTAINER
# =====================================================

class DAG:
    """
    Canonical DAG structure.

    FIXES:
    - accepts nodes in constructor OR empty init
    - prevents positional argument mismatch errors
    - provides consistent .nodes interface
    """

    def __init__(self, nodes: Optional[List[DAGNode]] = None):
        self.nodes: List[DAGNode] = nodes or []

    # -------------------------------------------------
    # ADD NODE
    # -------------------------------------------------

    def add_node(self, node: DAGNode):
        self.nodes.append(node)

    # -------------------------------------------------
    # SAFE ACCESS
    # -------------------------------------------------

    def get_node(self, node_id: str) -> Optional[DAGNode]:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        return None

    # -------------------------------------------------
    # SERIALIZATION (debugging / logging)
    # -------------------------------------------------

    def to_dict(self):
        return {
            "nodes": [n.to_dict() for n in self.nodes]
        }