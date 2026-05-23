from dataclasses import dataclass
from typing import List, Dict, Any
import re


@dataclass
class DAGNode:
    node_id: str
    tool: str
    args: Dict[str, Any]
    depends_on: List[str]


@dataclass
class DAG:
    nodes: List[DAGNode]


class DAGPlanner:
    """
    v1.1 Planner:
    - deterministic instruction decomposition
    - multi-step parsing
    - no truncation of input
    - explicit tool mapping
    """

    def __init__(self):
        pass

    # =====================================================
    # MAIN ENTRYPOINT
    # =====================================================

    def plan(self, goal: str) -> DAG:

        # -----------------------------
        # 1. PRESERVE FULL INPUT
        # -----------------------------
        full_goal = goal.strip()

        # -----------------------------
        # 2. SPLIT INTO INSTRUCTIONS
        # -----------------------------
        steps = self._extract_steps(full_goal)

        # -----------------------------
        # 3. BUILD DAG NODES
        # -----------------------------
        nodes = []
        prev_id = None

        for i, step in enumerate(steps):

            node_id = f"n{i}"

            tool, args = self._interpret_step(step)

            node = DAGNode(
                node_id=node_id,
                tool=tool,
                args=args,
                depends_on=[prev_id] if prev_id else []
            )

            nodes.append(node)
            prev_id = node_id

        return DAG(nodes=nodes)

    # =====================================================
    # STEP EXTRACTION (CRITICAL FIX)
    # =====================================================

    def _extract_steps(self, goal: str) -> List[str]:

        # Normalize line breaks first
        raw = goal.replace("\n", " ").strip()

        # Split ONLY on numbered steps like "1.", "2.", etc.
        pattern = r"\d+\.\s"

        parts = re.split(pattern, raw)

        # re.split produces leading empty string sometimes
        steps = [p.strip() for p in parts if p.strip()]

        # fallback: if no structured steps, treat whole goal as single instruction
        if not steps:
            return [raw]

        return steps

    # =====================================================
    # STEP INTERPRETER (TOOL MAPPING)
    # =====================================================

    def _interpret_step(self, step: str):

        step_lower = step.lower()

        # ---------------- FILE WRITE ----------------
        if "create" in step_lower and "write" not in step_lower:

            match = re.search(r"src/[^\s]+\.txt", step)
            filename = match.group(0) if match else "output.txt"

            content_match = re.search(r'"(.*?)"', step)
            content = content_match.group(1) if content_match else ""

            return "write_file", {
                "filename": filename,
                "content": content
            }

        # ---------------- FILE READ ----------------
        if "read" in step_lower:

            match = re.search(r"src/[^\s]+\.txt", step)
            filename = match.group(0) if match else ""

            return "read_file", {
                "filename": filename
            }

        # ---------------- LIST DIR ----------------
        if "list" in step_lower:

            return "list_dir", {}

        # ---------------- COMBINE / TRANSFORM ----------------
        if "combine" in step_lower or "reverse" in step_lower:

            # NOTE: placeholder deterministic transform step
            return "read_file", {
                "filename": "src/"  # intentionally signals multi-file dependency stage
            }

        # ---------------- DEFAULT FALLBACK ----------------
        return "list_dir", {}