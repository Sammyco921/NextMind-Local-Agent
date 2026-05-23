import re
from core.dag import DAG, DAGNode


# =====================================================
# PLANNER
# =====================================================

class DAGPlanner:
    """
    Deterministic semantic DAG compiler.
    """

    def plan(self, goal: str) -> DAG:

        dag = DAG()

        # Normalize separators
        steps = [
            s.strip()
            for s in re.split(r",|then", goal)
            if s.strip()
        ]

        previous_node = None
        node_counter = 0

        read_targets = []

        # =================================================
        # INTENT HELPERS
        # =================================================

        def extract_filename(text: str):
            match = re.search(r'([\w\/\-]+\.\w+)', text)
            return match.group(1) if match else None

        def extract_content(text: str):
            match = re.search(r'"([^"]*)"', text)
            return match.group(1) if match else ""

        def new_node(tool, args, depends=None):
            nonlocal node_counter, previous_node

            node = DAGNode(
                node_id=f"n{node_counter}",
                tool=tool,
                args=args,
                depends_on=depends or ([previous_node] if previous_node else [])
            )

            node_counter += 1
            previous_node = node.node_id
            dag.add_node(node)

            return node

        # =================================================
        # STEP EXECUTION
        # =================================================

        for step in steps:

            step_lower = step.lower()

            # -------------------------------------------------
            # 1. PROJECT STRUCTURE (FIXED)
            # -------------------------------------------------
            # Previously: ignored or crashed
            # Now: explicitly mapped to mkdir simulation via writes

            if "project folder" in step_lower or "structure" in step_lower:

                # We do NOT assume mkdir tool exists.
                # We simulate structure via marker files.

                new_node("write_file", {
                    "filename": "src/.keep",
                    "content": ""
                })

                new_node("write_file", {
                    "filename": "logs/.keep",
                    "content": ""
                })

                continue

            # -------------------------------------------------
            # 2. WRITE FILE
            # -------------------------------------------------

            if "create" in step_lower or "write" in step_lower:

                filename = extract_filename(step)
                content = extract_content(step)

                if not filename:
                    raise ValueError(f"Missing filename in step: {step}")

                new_node("write_file", {
                    "filename": filename,
                    "content": content
                })

                continue

            # -------------------------------------------------
            # 3. READ FILE
            # -------------------------------------------------

            if "read" in step_lower:

                filename = extract_filename(step)

                if not filename:
                    raise ValueError(f"Missing filename in step: {step}")

                read_targets.append(filename)

                new_node("read_file", {
                    "filename": filename
                })

                continue

            # -------------------------------------------------
            # 4. TRANSFORM (FIXED CONTRACT)
            # -------------------------------------------------

            if (
                "reverse" in step_lower
                or "processed" in step_lower
                or "combine" in step_lower
                or "transform" in step_lower
            ):

                new_node("transform", {
                    "operation": "reverse_and_concat",
                    "input_files": read_targets.copy(),
                    "output": "processed.txt"
                })

                continue

            # -------------------------------------------------
            # 5. LIST DIRECTORY
            # -------------------------------------------------

            if "list" in step_lower:

                new_node("list_dir", {})

                continue

        return dag