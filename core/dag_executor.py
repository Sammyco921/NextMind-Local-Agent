from typing import Dict, Any


class DAGExecutor:
    """
    Deterministic DAG executor.

    Key fixes:
    - Enforces registry validation BEFORE execution
    - Removes silent arg mutation
    - Standardizes error reporting
    - Guarantees tool contract compliance
    """

    def __init__(self, registry):
        self.registry = registry
        self.node_outputs: Dict[str, Any] = {}

    # =========================================================
    # MAIN EXECUTION ENTRY
    # =========================================================

    def execute(self, dag):
        """
        Executes DAG in topological order.
        """

        results = {}

        for node in dag.nodes:
            try:
                result = self._execute_node(node, results)
                results[node.node_id] = result

            except Exception as e:
                results[node.node_id] = {
                    "status": "failed",
                    "error": str(e)
                }

        return results

    # =========================================================
    # NODE EXECUTION
    # =========================================================

    def _execute_node(self, node, results: Dict[str, Any]):

        tool_name = node.tool
        args = dict(node.args)  # copy to avoid mutation side effects

        # -----------------------------------------------------
        # CRITICAL FIX: validate against registry BEFORE run
        # -----------------------------------------------------

        if not self.registry.has(tool_name):
            raise ValueError(f"Unknown tool: {tool_name}")

        self.registry.validate_args(tool_name, args)

        handler = self.registry.handler(tool_name)

        # -----------------------------------------------------
        # EXECUTION
        # -----------------------------------------------------

        output = handler(**args)

        # store output for downstream nodes
        self.node_outputs[node.node_id] = output

        return output

    # =========================================================
    # OPTIONAL DEBUG HELPERS
    # =========================================================

    def get_outputs(self):
        return self.node_outputs

    def reset(self):
        self.node_outputs = {}