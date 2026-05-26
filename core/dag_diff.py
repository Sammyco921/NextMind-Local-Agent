from typing import Dict, Any, Set


class DAGDiff:
    """
    Computes structural differences between two DAG states
    """

    def diff(self, old_dag, new_dag) -> Dict[str, Any]:

        old_nodes = old_dag.nodes
        new_nodes = new_dag.nodes

        old_ids = set(old_nodes.keys())
        new_ids = set(new_nodes.keys())

        added = new_ids - old_ids
        removed = old_ids - new_ids
        common = old_ids & new_ids

        modified = []
        preserved = []

        # -------------------------------------------------
        # Compare shared nodes
        # -------------------------------------------------

        for node_id in common:

            old = old_nodes[node_id]
            new = new_nodes[node_id]

            if self._is_modified(old, new):
                modified.append(node_id)
            else:
                preserved.append(node_id)

        return {
            "added": list(added),
            "removed": list(removed),
            "modified": modified,
            "preserved": preserved
        }

    # =====================================================
    # NODE COMPARISON
    # =====================================================

    def _is_modified(self, old_node, new_node) -> bool:

        return (
            old_node.tool != new_node.tool or
            old_node.args != new_node.args or
            old_node.depends_on != new_node.depends_on
        )