# tests/test_v19_behavioral.py — updated for v1.9.1 stage boundaries

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.strict_pipeline import StrictPipeline
from core.tool_registry import ToolRegistry
from core.tool_schemas import TOOL_SCHEMAS
from tools.list_dir import list_dir
from tools.read_file import read_file
from tools.write_file import write_file


def _pipeline() -> StrictPipeline:
    registry = ToolRegistry()
    registry.register("write_file", write_file, TOOL_SCHEMAS["write_file"])
    registry.register("read_file", read_file, TOOL_SCHEMAS["read_file"])
    registry.register("list_dir", list_dir, TOOL_SCHEMAS["list_dir"])
    return StrictPipeline(registry)


def test_exact_filename_preservation():
    goal = '1. create src/exact_name.txt with "x"\n2. list files in src directory'
    result = _pipeline().run(goal)
    assert result.status == "success", result.failure
    assert os.path.exists("src/exact_name.txt")


def test_unquoted_content_fails_at_validation_or_dag_not_parsing():
    goal = "create src/noquotes.txt without quoted content"
    result = _pipeline().run(goal)
    # v1.9: ambiguous "without quoted content" is PARTIAL → clarification_required
    assert result.status in ("failed", "clarification_required"), (
        f"Expected failed or clarification_required, got {result.status}"
    )
    if result.status == "failed":
        assert result.failed_stage != "parsing"


def test_no_execution_without_validation_pass():
    goal = "combine only: input_a.txt input_b.txt into out.txt"
    result = _pipeline().run(goal)
    # v1.9: missing explicit content → PARTIAL → clarification_required
    assert result.status in ("failed", "clarification_required"), (
        f"Expected failed or clarification_required, got {result.status}"
    )
    if result.status == "failed" and result.execution is not None:
        assert result.failed_stage == "execution"


def test_ordering_preserved_demo():
    goal = """
1. create src/a.txt with "a"
2. create src/b.txt with "b"
3. read src/a.txt
4. read src/b.txt
5. create src/result.txt with combined reversed content
6. list files in src directory
""".strip()
    result = _pipeline().run(goal)
    assert result.status == "success", result.failure
    assert [t["id"] for t in result.execution.trace] == [
        "n0", "n1", "n2", "n3", "n4", "n5"
    ]


def test_char_reverse_exact():
    goal = """
1. create src/x.txt with "ab"
2. create src/y.txt with "cd"
3. read src/x.txt
4. read src/y.txt
5. create src/result.txt with combined reversed content
""".strip()
    result = _pipeline().run(goal)
    assert result.status == "success", result.failure
    with open("src/result.txt", encoding="utf-8") as f:
        assert f.read() == "dcba"


if __name__ == "__main__":
    test_exact_filename_preservation()
    test_unquoted_content_fails_at_validation_or_dag_not_parsing()
    test_no_execution_without_validation_pass()
    test_ordering_preserved_demo()
    test_char_reverse_exact()
    print("ALL v1.9 BEHAVIORAL TESTS PASSED")
