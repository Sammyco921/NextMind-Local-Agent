from core.dag import DAG


class Replanner:

    def __init__(self, planner):
        self.planner = planner

    def replan(
        self,
        goal,
        current_dag,
        failure_context
    ):
        """
        Simple recovery strategy:
        regenerate a fresh DAG from the original goal.
        """

        return self.planner.plan(goal)

    def diff_dags(self, old_dag, new_dag):

        old_ids = set(old_dag.nodes.keys())
        new_ids = set(new_dag.nodes.keys())

        added = list(new_ids - old_ids)
        removed = list(old_ids - new_ids)

        modified = []
        preserved = []

        for node_id in old_ids.intersection(new_ids):

            old_node = old_dag.nodes[node_id]
            new_node = new_dag.nodes[node_id]

            if (
                old_node.tool != new_node.tool
                or old_node.args != new_node.args
                or old_node.depends_on != new_node.depends_on
            ):
                modified.append(node_id)
            else:
                preserved.append(node_id)

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "preserved": preserved
        }