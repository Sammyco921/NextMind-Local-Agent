# core/decomposer.py
#
# Complex-goal decomposition → atomic tool-level structured steps (DAG-compatible).
# Deterministic rule table: first-category-match wins, no signal counting.
#
# INVARIANT: Decomposer is stateless — intent → rule-mapped steps only.
# No component may depend on previous executions of decompose().

from __future__ import annotations

import re
from typing import List, Optional

from core.artifact_refs import artifact_ref, combine_reverse_sources
from core.planning_types import StructuredStep


# Explicit rule table: each keyword set maps to a fixed structure size.
# First match wins — no computed signal strength.
_MULTI_DEPENDENCY_KEYWORDS = frozenset({
    "multi-step", "dag", "workflow", "deterministic", "dependencies",
})
_FILE_PIPELINE_KEYWORDS = frozenset({
    "pipeline", "process", "file", "combine",
})


class Decomposer:
    """
    Intent compiler for complex/system goals.
    Outputs only atomic tool operations — no natural language in final steps.
    Uses explicit category matching (keyword set → fixed structure).
    """

    def decompose(self, goal: str) -> List[StructuredStep]:
        raw = (goal or "").strip()
        if not raw:
            return []

        lowered = raw.lower()
        category = self._categorize(lowered)

        if category == "word_order":
            return self._word_order_file_workflow(lowered)
        if category == "multi_dependency":
            return self._dependency_pipeline(raw, lowered)
        if category == "file_pipeline":
            return self._file_processing_pipeline(raw, lowered)
        return []

    def _categorize(self, lowered: str) -> Optional[str]:
        """Explicit rule table — first match wins, no signal counting."""
        if self._is_word_order_workflow(lowered):
            return "word_order"
        if any(k in lowered for k in _MULTI_DEPENDENCY_KEYWORDS):
            return "multi_dependency"
        if any(k in lowered for k in _FILE_PIPELINE_KEYWORDS):
            return "file_pipeline"
        return None

    def _is_word_order_workflow(self, lowered: str) -> bool:
        return bool(
            ("word" in lowered and "reverse" in lowered)
            or "word order" in lowered
        ) and bool(
            "file" in lowered
            or "workflow" in lowered
            or "two" in lowered
            or "combine" in lowered
        )

    def _word_order_file_workflow(self, lowered: str) -> List[StructuredStep]:
        """
        Hypothesis plan: reads two files, combine + reverse.
        Initial transform is char-level combine_reverse; evaluator + repair
        converge to word-level combine_reverse_words when required.
        """
        work_dir = "src"
        if "workspace" in lowered:
            work_dir = "workspace"

        file_a = f"{work_dir}/file_a.txt"
        file_b = f"{work_dir}/file_b.txt"
        output = f"{work_dir}/result.txt"

        return [
            {
                "id": "d0",
                "action": "bootstrap_write",
                "tool": "write_file",
                "args": {"filename": file_a, "content": "hello world"},
                "dependencies": [],
            },
            {
                "id": "d1",
                "action": "bootstrap_write",
                "tool": "write_file",
                "args": {"filename": file_b, "content": "foo bar"},
                "dependencies": [],
            },
            {
                "id": "d2",
                "action": "read",
                "tool": "read_file",
                "args": {"filename": file_a},
                "dependencies": ["d0"],
            },
            {
                "id": "d3",
                "action": "read",
                "tool": "read_file",
                "args": {"filename": file_b},
                "dependencies": ["d1"],
            },
            {
                "id": "d4",
                "action": "process_write",
                "tool": "write_file",
                "args": {
                    "filename": output,
                    "content": combine_reverse_sources(["d2", "d3"]),
                },
                "dependencies": ["d2", "d3"],
            },
            {
                "id": "d5",
                "action": "verify_list",
                "tool": "list_dir",
                "args": {"path": work_dir},
                "dependencies": ["d4"],
            },
        ]

    def _dependency_pipeline(self, raw: str, lowered: str) -> List[StructuredStep]:
        """Fixed 6-node structure for multi-dependency goals."""
        work_dir = "src"
        if "workspace" in lowered:
            work_dir = "workspace"
        elif m := re.search(r"(src/[\w.-]+)", raw):
            work_dir = m.group(1).split("/")[0] if "/" in m.group(1) else "src"

        input_a = f"{work_dir}/input_a.txt"
        input_b = f"{work_dir}/input_b.txt"
        output = f"{work_dir}/result.txt" if "result" in lowered else f"{work_dir}/processed.txt"

        combine_reverse = "reverse" in lowered or "combined" in lowered

        content_ref = (
            combine_reverse_sources(["d2", "d3"])
            if combine_reverse
            else {
                "$transform": "combine",
                "$sources": [artifact_ref("d2"), artifact_ref("d3")],
            }
        )

        return [
            {
                "id": "d0",
                "action": "bootstrap_write",
                "tool": "write_file",
                "args": {"filename": input_a, "content": "pipeline_input_a"},
                "dependencies": [],
            },
            {
                "id": "d1",
                "action": "bootstrap_write",
                "tool": "write_file",
                "args": {"filename": input_b, "content": "pipeline_input_b"},
                "dependencies": [],
            },
            {
                "id": "d2",
                "action": "read",
                "tool": "read_file",
                "args": {"filename": input_a},
                "dependencies": ["d0"],
            },
            {
                "id": "d3",
                "action": "read",
                "tool": "read_file",
                "args": {"filename": input_b},
                "dependencies": ["d1"],
            },
            {
                "id": "d4",
                "action": "process_write",
                "tool": "write_file",
                "args": {"filename": output, "content": content_ref},
                "dependencies": ["d2", "d3"],
            },
            {
                "id": "d5",
                "action": "verify_list",
                "tool": "list_dir",
                "args": {"path": work_dir},
                "dependencies": ["d4"],
            },
        ]

    def _file_processing_pipeline(self, raw: str, lowered: str) -> List[StructuredStep]:
        """Fixed 4-node structure for file/process pipeline goals."""
        work_dir = "src"
        if "workspace" in lowered:
            work_dir = "workspace"
        elif m := re.search(r"(src/[\w.-]+)", raw):
            work_dir = m.group(1).split("/")[0] if "/" in m.group(1) else "src"

        input_a = f"{work_dir}/input_a.txt"
        output = f"{work_dir}/result.txt" if "result" in lowered else f"{work_dir}/processed.txt"

        content_ref = {
            "$transform": "combine",
            "$sources": [artifact_ref("d1")],
        }

        return [
            {
                "id": "d0",
                "action": "bootstrap_write",
                "tool": "write_file",
                "args": {"filename": input_a, "content": "pipeline_input_a"},
                "dependencies": [],
            },
            {
                "id": "d1",
                "action": "read",
                "tool": "read_file",
                "args": {"filename": input_a},
                "dependencies": ["d0"],
            },
            {
                "id": "d2",
                "action": "process_write",
                "tool": "write_file",
                "args": {"filename": output, "content": content_ref},
                "dependencies": ["d1"],
            },
        ]


