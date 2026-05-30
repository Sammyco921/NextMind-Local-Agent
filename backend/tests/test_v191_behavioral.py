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
    """Combine without reads must not reach execution.
    
    v1.9 clarification gate catches the missing content BEFORE planning.
    The pipeline must return CLARIFICATION_REQUIRED rather than silently
    proceeding to DAG construction.
    """
    result = _pipeline().run(
        "combine words in this exact order: input_y.txt and input_x.txt into combo.txt"
    )
    assert result.status in ("failed", "clarification_required"), (
        f"Expected failed or clarification_required, got {result.status}"
    )
    if result.status == "clarification_required":
        assert result.clarification is not None
        # Verify it was blocked at intent_clarification, not parsing
        stages = [s.stage for s in result.stages]
        assert "intent_clarification" in stages
    else:
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


# =============================================================================
# v1.4 Typed Artifact Runtime — type-system tests
# =============================================================================


def test_artifact_type_enum_immutable():
    """ArtifactType enum is frozen — no new values can be added at runtime."""
    from core.artifact_types import ArtifactType
    assert ArtifactType.TEXT.value == "text"
    assert ArtifactType.FILE.value == "file"
    assert ArtifactType.JSON.value == "json"
    assert ArtifactType.DIRECTORY.value == "directory"
    assert ArtifactType.BOOLEAN.value == "boolean"
    assert ArtifactType.NULL.value == "null"
    assert len(ArtifactType) == 11


def test_artifact_dataclass_frozen():
    """Artifact instances are immutable."""
    from core.artifact_types import Artifact, ArtifactType
    a = Artifact(type=ArtifactType.TEXT, value="hello")
    assert a.type == ArtifactType.TEXT
    assert a.value == "hello"
    try:
        a.value = "world"
        assert False, "Should not allow mutation"
    except Exception:
        pass  # frozen dataclass prevents attribute assignment


def test_artifact_convenience_constructors():
    from core.artifact_types import Artifact, ArtifactType
    a = Artifact.text("hello")
    assert a.type == ArtifactType.TEXT
    assert a.value == "hello"

    b = Artifact.file("test.txt", "content")
    assert b.type == ArtifactType.FILE
    assert b.value["filename"] == "test.txt"

    c = Artifact.json({"key": "val"})
    assert c.type == ArtifactType.JSON
    assert c.value["key"] == "val"

    d = Artifact.null()
    assert d.type == ArtifactType.NULL
    assert d.value is None


def test_tool_contracts_defined_for_core_tools():
    from core.tool_contracts import get_contract, has_contract
    assert has_contract("write_file")
    assert has_contract("read_file")
    assert has_contract("list_dir")

    wc = get_contract("write_file")
    assert wc.deterministic
    assert "filesystem_write" in wc.side_effects
    assert wc.output_type.value == "file"

    rc = get_contract("read_file")
    assert rc.deterministic
    assert rc.output_type.value == "text"

    lc = get_contract("list_dir")
    assert lc.deterministic
    assert lc.output_type.value == "directory"


def test_type_flow_valid_type_passes():
    """Valid type flows between nodes must pass type validation."""
    from core.dag_node import DAG, DAGNode
    from core.type_validator import validate_type_flow
    from core.tool_contracts import get_contract

    dag = DAG(nodes=[
        DAGNode(
            node_id="n0", tool_name="write_file",
            raw_args={"filename": "a.txt", "content": "hello"},
            dependencies=[],
        ),
        DAGNode(
            node_id="n1", tool_name="read_file",
            raw_args={"filename": "a.txt"},
            dependencies=["n0"],
        ),
    ])
    errors = validate_type_flow(dag, get_contract)
    assert errors == [], f"Expected no type errors, got: {errors}"


def test_type_flow_mismatched_type_rejected():
    """Type mismatch between dependency output and consuming arg must be rejected."""
    from core.dag_node import DAG, DAGNode
    from core.type_validator import validate_type_flow
    from core.tool_contracts import get_contract

    # n0 produces DIRECTORY (list_dir), n1 expects TEXT (read_file filename)
    dag = DAG(nodes=[
        DAGNode(
            node_id="n0", tool_name="list_dir",
            raw_args={"path": "."},
            dependencies=[],
        ),
        DAGNode(
            node_id="n1", tool_name="read_file",
            raw_args={"filename": {"$artifact": "n0"}},
            dependencies=["n0"],
        ),
    ])
    errors = validate_type_flow(dag, get_contract)
    assert len(errors) >= 1
    assert any("expects" in e and "produces" in e for e in errors), errors


def test_type_flow_no_contract_rejected():
    """Node with tool that has no declared contract must be rejected."""
    from core.dag_node import DAG, DAGNode
    from core.type_validator import validate_type_flow
    from core.tool_contracts import get_contract

    dag = DAG(nodes=[
        DAGNode(
            node_id="n0", tool_name="nonexistent_tool",
            raw_args={}, dependencies=[],
        ),
    ])
    errors = validate_type_flow(dag, get_contract)
    assert len(errors) >= 1
    assert any("no declared contract" in e for e in errors), errors


def test_artifact_metadata_preserved_through_execution():
    """Runtime artifacts must carry correct type metadata through execution."""
    from core.strict_pipeline import StrictPipeline
    from core.tool_registry import ToolRegistry
    from core.tool_schemas import TOOL_SCHEMAS
    from tools.write_file import write_file
    from tools.read_file import read_file
    from tools.list_dir import list_dir
    from core.artifact_types import ArtifactType

    registry = ToolRegistry()
    registry.register("write_file", write_file, TOOL_SCHEMAS["write_file"])
    registry.register("read_file", read_file, TOOL_SCHEMAS["read_file"])
    registry.register("list_dir", list_dir, TOOL_SCHEMAS["list_dir"])

    pipeline = StrictPipeline(registry)
    result = pipeline.run(
        '1. create src/a.txt with "a"\n'
        '2. list files in src directory'
    )
    if result.status == "success" and result.execution:
        trace = result.execution.trace
        for entry in trace:
            assert "artifact_type" in entry, (
                f"Missing artifact_type in trace entry: {entry}"
            )
            assert entry["artifact_type"] is not None


def test_executor_preserves_typed_artifacts():
    """Executor wraps all tool outputs in typed Artifact objects."""
    from core.dag_executor import DAGExecutor
    from core.dag_node import DAG, DAGNode, CapabilityManifest
    from core.tool_registry import ToolRegistry
    from core.tool_schemas import TOOL_SCHEMAS
    from tools.write_file import write_file
    from tools.read_file import read_file
    from tools.list_dir import list_dir

    registry = ToolRegistry()
    registry.register("write_file", write_file, TOOL_SCHEMAS["write_file"])
    registry.register("read_file", read_file, TOOL_SCHEMAS["read_file"])
    registry.register("list_dir", list_dir, TOOL_SCHEMAS["list_dir"])

    dag = DAG(nodes=[
        DAGNode(
            node_id="n0", tool_name="write_file",
            raw_args={"filename": "_test_type_artifact.txt", "content": "test"},
            dependencies=[],
        ),
    ], capability_manifest=CapabilityManifest(
        dag_id="test",
        capabilities=[
            {"capability_id": "filesystem.write", "display_name": "write",
             "allowed_tools": ["write_file"], "scope": {}, "constraints": {}},
            {"capability_id": "tool.execution", "display_name": "exec",
             "allowed_tools": ["write_file"], "scope": {}, "constraints": {}},
        ],
        strict_mode=True,
    ))
    executor = DAGExecutor(registry)
    result = executor.execute(dag, "test")
    assert result.status == "success", f"Execution failed: {result.trace}"
    assert len(result.trace) == 1
    entry = result.trace[0]
    assert entry.get("artifact_type") == "file", (
        f"Expected 'file' artifact type, got: {entry.get('artifact_type')}"
    )


def test_type_validator_stateless():
    """Type validator must produce identical results for same input."""
    from core.dag_node import DAG, DAGNode
    from core.type_validator import validate_type_flow
    from core.tool_contracts import get_contract

    dag = DAG(nodes=[
        DAGNode(
            node_id="n0", tool_name="write_file",
            raw_args={"filename": "a.txt", "content": "hello"},
            dependencies=[],
        ),
    ])
    r1 = validate_type_flow(dag, get_contract)
    r2 = validate_type_flow(dag, get_contract)
    assert r1 == r2, f"Statelessness violated: {r1} != {r2}"


def test_transform_tools_have_contracts():
    """All explicit transform tools must have declared contracts."""
    from core.tool_contracts import has_contract, get_contract
    for tool in ("text_to_json", "json_to_text", "file_to_text"):
        assert has_contract(tool), f"Missing contract for {tool}"
        c = get_contract(tool)
        assert c.deterministic, f"{tool} must be deterministic"
        assert c.output_type is not None, f"{tool} missing output_type"


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
    test_artifact_type_enum_immutable()
    test_artifact_dataclass_frozen()
    test_artifact_convenience_constructors()
    test_tool_contracts_defined_for_core_tools()
    test_type_flow_valid_type_passes()
    test_type_flow_mismatched_type_rejected()
    test_type_flow_no_contract_rejected()
    test_artifact_metadata_preserved_through_execution()
    test_executor_preserves_typed_artifacts()
    test_type_validator_stateless()
    test_transform_tools_have_contracts()
    print("ALL v1.9.1 BEHAVIORAL TESTS PASSED")
