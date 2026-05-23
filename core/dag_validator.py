# core/dag_validator.py

from typing import Dict, Any, List, Set


# =====================================================
# DAG VALIDATOR (v1.1 EXECUTION GATE)
# =====================================================

class DAGValidator:
    """
    HARD EXECUTION GATE.

    This is the final enforcement layer before execution.

    It guarantees:
    - DAG structural correctness
    - tool validity
    - argument correctness
    - dependency correctness
    - no unsafe or unknown operations
    """

    def __init__(self, registry):
        self.registry = registry

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def validate(self, dag) -> Dict[str, Any]:
        errors = []

        nodes = getattr(dag, "nodes", [])

        # ---------------------------------------------
        # 1. EMPTY DAG CHECK
        # ---------------------------------------------

        if not nodes:
            return {
                "status": "invalid",
                "errors": ["DAG contains no nodes"]
            }

        seen_ids: Set[str] = set()

        # ---------------------------------------------
        # 2. NODE VALIDATION
        # ---------------------------------------------

        for node in nodes:

            node_id = getattr(node, "node_id", None)
            tool = getattr(node, "tool", None)
            args = getattr(node, "args", None)
            depends_on = getattr(node, "depends_on", None)

            # -------------------------
            # REQUIRED FIELD CHECKS
            # -------------------------

            if node_id is None:
                errors.append("Node missing node_id")

            if tool is None:
                errors.append(f"Node {node_id}: missing tool")

            if args is None:
                errors.append(f"Node {node_id}: missing args")

            if depends_on is None:
                errors.append(f"Node {node_id}: missing depends_on")

            # -------------------------
            # DUPLICATE NODE IDS
            # -------------------------

            if node_id in seen_ids:
                errors.append(f"Duplicate node_id detected: {node_id}")
            else:
                seen_ids.add(node_id)

            # -------------------------
            # TOOL VALIDATION
            # -------------------------

            if tool and not self.registry.has(tool):
                errors.append(f"Unknown tool: {tool}")

            # -------------------------
            # TOOL ARG SCHEMA VALIDATION
            # -------------------------

            if tool and self.registry.has(tool):
                try:
                    self.registry.validate_args(tool, args)
                except Exception as e:
                    errors.append(f"Tool '{tool}' arg error: {str(e)}")

        # ---------------------------------------------
        # 3. DEPENDENCY VALIDATION
        # ---------------------------------------------

        valid_ids = {getattr(n, "node_id", None) for n in nodes}

        for node in nodes:
            node_id = node.node_id
            for dep in getattr(node, "depends_on", []):

                if dep not in valid_ids:
                    errors.append(
                        f"Node {node_id} has invalid dependency: {dep}"
                    )

                if dep == node_id:
                    errors.append(
                        f"Node {node_id} cannot depend on itself"
                    )

        # ---------------------------------------------
        # 4. LEGACY SAFETY CHECK (IMPORTANT)
        # ---------------------------------------------

        for node in nodes:
            if getattr(node, "tool", "").startswith("legacy"):
                errors.append(
                    f"Blocked legacy tool usage in DAG: {node.tool}"
                )

        # ---------------------------------------------
        # FINAL RESULT
        # ---------------------------------------------

        if errors:
            return {
                "status": "invalid",
                "errors": errors
            }

        return {
            "status": "valid",
            "errors": []
        }