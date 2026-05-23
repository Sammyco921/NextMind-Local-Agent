from typing import Dict, Any, List


# =====================================================
# VALIDATOR
# =====================================================

class DAGValidator:
    """
    Hard validation layer for DAG correctness.
    """

    def __init__(self, registry):
        self.registry = registry

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def validate(self, dag) -> Dict[str, Any]:

        errors: List[str] = []

        nodes = getattr(dag, "nodes", [])

        # -------------------------------------------------
        # EMPTY DAG CHECK
        # -------------------------------------------------

        if not nodes:
            return {
                "status": "invalid",
                "errors": ["DAG is empty"]
            }

        # -------------------------------------------------
        # NODE VALIDATION
        # -------------------------------------------------

        for node in nodes:

            tool = node.tool
            args = node.args or {}

            # -------------------------------------------------
            # TOOL EXISTS CHECK (FIXED CRASH YOU SAW)
            # -------------------------------------------------

            if not self.registry.has(tool):
                errors.append(f"{node.node_id}: unknown tool '{tool}'")
                continue

            meta = self.registry.get_metadata(tool)

            # -------------------------------------------------
            # BASIC ARG VALIDATION
            # -------------------------------------------------

            if tool == "write_file":

                filename = args.get("filename")

                if not filename:
                    errors.append(f"{node.node_id}: missing filename")
                    continue

                if filename == "output.txt":
                    errors.append(f"{node.node_id}: placeholder filename 'output.txt' not allowed")

                if filename.strip() == "":
                    errors.append(f"{node.node_id}: empty filename")

                content = args.get("content", None)
                if content is None:
                    errors.append(f"{node.node_id}: missing content for write_file")

            # -------------------------------------------------
            # READ FILE VALIDATION
            # -------------------------------------------------

            elif tool == "read_file":

                filename = args.get("filename")

                if not filename:
                    errors.append(f"{node.node_id}: missing filename")

                if filename == "output.txt":
                    errors.append(f"{node.node_id}: invalid placeholder file usage")

            # -------------------------------------------------
            # TRANSFORM VALIDATION (CRITICAL FIX)
            # -------------------------------------------------

            elif tool == "transform":

                if "operation" not in args:
                    errors.append(f"{node.node_id}: missing operation in transform")

                if "input_files" not in args:
                    errors.append(f"{node.node_id}: missing input_files in transform")

                if not isinstance(args.get("input_files"), list):
                    errors.append(f"{node.node_id}: input_files must be list")

                if not args.get("input_files"):
                    errors.append(f"{node.node_id}: transform has empty input_files")

                if args.get("output") != "processed.txt":
                    errors.append(f"{node.node_id}: transform must output processed.txt")

            # -------------------------------------------------
            # LIST DIR VALIDATION
            # -------------------------------------------------

            elif tool == "list_dir":

                # no strict args required
                pass

            # -------------------------------------------------
            # UNKNOWN TOOL SAFETY
            # -------------------------------------------------

            else:
                errors.append(f"{node.node_id}: unsupported tool '{tool}'")

        # -------------------------------------------------
        # FINAL RESULT
        # -------------------------------------------------

        if errors:
            return {
                "status": "invalid",
                "errors": errors
            }

        return {
            "status": "valid",
            "errors": []
        }