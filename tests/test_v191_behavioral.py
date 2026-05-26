# tests/test_v191_behavioral.py

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.goal_normalizer import GoalNormalizer
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


def test_normalizer_accepts_typo_create_directory():
    n = GoalNormalizer().normalize("crete a directory workspace/alpha/")
    assert len(n.normalized_steps) == 1
    assert n.normalized_steps[0].type_guess == "create_dir"
    assert "workspace/alpha" in str(n.normalized_steps[0].entities)


def test_normalizer_does_not_fail_missing_quotes():
    n = GoalNormalizer().normalize(
        "create file workspace/alpha/input_y.txt ith content delta"
    )
    assert len(n.normalized_steps) == 1
    assert n.normalized_steps[0].entities.get("content") == "delta"


def test_missing_quotes_not_parsing_failure():
    result = _pipeline().run(
        "create file workspace/alpha/input_y.txt ith content delta"
    )
    assert result.failed_stage != "parsing", result.failure


def test_create_file_with_exact_content_runs():
    goal = (
        'create file under workspace/alpha/ called input_x.txt '
        'with the exact content: "alpha beta gamma"'
    )
    result = _pipeline().run(goal)
    assert result.status == "success", result.failure
    assert os.path.exists("workspace/alpha/input_x.txt")
    with open("workspace/alpha/input_x.txt", encoding="utf-8") as f:
        assert f.read() == "alpha beta gamma"


def test_combine_without_reads_fails_not_at_parsing():
    """Combine without reads must fail, but NOT at parsing stage.
    
    The failure can occur at dag_construction, pre_execution_validation,
    execution, or semantic_evaluation - but never at parsing.
    """
    result = _pipeline().run(
        "combine words in this exact order: input_y.txt and input_x.txt into combo.txt"
    )
    assert result.status == "failed"
    # Must fail at a stage after parsing (not at parsing itself)
    assert result.failed_stage in (
        "dag_construction",
        "pre_execution_validation",
        "execution",
        "semantic_evaluation",
    )


def test_v19_demo_still_passes():
    goal = """
1. create src/a.txt with "a"
2. create src/b.txt with "b"
3. read src/a.txt
4. read src/b.txt
5. create src/result.txt with combined reversed content
""".strip()
    result = _pipeline().run(goal)
    assert result.status == "success", result.failure


def test_dag_determinism():
    """Identical inputs must produce identical DAG structures (pure determinism)."""
    pipeline = _pipeline()
    goal = '1. create src/a.txt with "a"\n2. create src/b.txt with "b"\n3. list files in src directory'
    r1 = pipeline.run(goal)
    r2 = pipeline.run(goal)
    assert r1.status == r2.status, f"determinism broken: {r1.status} != {r2.status}"
    if r1.status == "success" and r2.status == "success":
        p1 = r1.plan
        p2 = r2.plan
        assert p1.step_count == p2.step_count, (
            f"determinism: node count mismatch {p1.step_count} != {p2.step_count}"
        )
        for n1, n2 in zip(p1.dag.nodes, p2.dag.nodes):
            assert n1.node_id == n2.node_id, f"node_id mismatch: {n1.node_id} != {n2.node_id}"
            assert n1.tool_name == n2.tool_name, f"tool mismatch: {n1.tool_name} != {n2.tool_name}"


def test_dag_non_collapse():
    """Different intent types must produce structurally different DAGs."""
    pipeline = _pipeline()
    simple_complex_pairs = [
        ('1. create src/x.txt with "x"', "pipeline system with dependencies"),
        ('create src/a.txt with "hello"', "multi-step processing dag"),
    ]
    for simple_goal, complex_goal in simple_complex_pairs:
        r1 = pipeline.run(simple_goal)
        r2 = pipeline.run(complex_goal)
        if r1.status == "success" and r2.status == "success":
            p1, p2 = r1.plan, r2.plan
            sig1 = (p1.step_count, tuple(n.tool_name for n in p1.dag.nodes))
            sig2 = (p2.step_count, tuple(n.tool_name for n in p2.dag.nodes))
            assert sig1 != sig2, (
                f"Non-collapse violation: simple '{simple_goal}' and complex "
                f"'{complex_goal}' produced same DAG profile {sig1}"
            )


def test_structural_variance():
    """Same intent, different inputs must produce non-identical DAGs (within-category variance)."""
    pipeline = _pipeline()
    # Two different simple file-create goals
    r1 = pipeline.run('create src/alpha.txt with "hello world"')
    r2 = pipeline.run('create src/beta.txt with "foo bar"')
    if r1.status == "success" and r2.status == "success":
        p1, p2 = r1.plan, r2.plan
        sig1 = (p1.step_count, tuple(n.tool_name for n in p1.dag.nodes),
                tuple(n.raw_args.get("filename") for n in p1.dag.nodes if n.tool_name == "write_file"))
        sig2 = (p2.step_count, tuple(n.tool_name for n in p2.dag.nodes),
                tuple(n.raw_args.get("filename") for n in p2.dag.nodes if n.tool_name == "write_file"))
        assert sig1 != sig2, (
            f"Structural variance violation: same intent, different inputs "
            f"produced identical DAG {sig1}"
        )


def test_validator_bitwise_determinism():
    """Same DAG input always produces identical validation result (pure function)."""
    from core.dag_node import DAG, DAGNode
    from core.dag_validator import DAGValidator
    from core.tool_registry import ToolRegistry
    from core.tool_schemas import TOOL_SCHEMAS

    registry = ToolRegistry()
    registry.register("write_file", write_file, TOOL_SCHEMAS["write_file"])
    registry.register("read_file", read_file, TOOL_SCHEMAS["read_file"])

    dag = DAG(nodes=[
        DAGNode(node_id="n0", tool_name="write_file",
                raw_args={"filename": "test.txt", "content": "hello"},
                dependencies=[]),
        DAGNode(node_id="n1", tool_name="read_file",
                raw_args={"filename": "test.txt"},
                dependencies=["n0"]),
    ])

    v = DAGValidator(registry)
    r1 = v.validate(dag)
    r2 = v.validate(dag)
    assert r1 == r2, (
        f"Bitwise determinism broken: {r1} != {r2}"
    )


if __name__ == "__main__":
    test_normalizer_accepts_typo_create_directory()
    test_normalizer_does_not_fail_missing_quotes()
    test_missing_quotes_not_parsing_failure()
    test_create_file_with_exact_content_runs()
    test_combine_without_reads_fails_not_at_parsing()
    test_v19_demo_still_passes()
    test_dag_determinism()
    test_dag_non_collapse()
    test_structural_variance()
    test_validator_bitwise_determinism()
    print("ALL v1.9.1 BEHAVIORAL TESTS PASSED")
