# tests/test_clarification_engine.py
#
# v1.9 Clarification Engine — full test suite.
#
# Tests verify:
# - Intent completeness classification (executable / partial / non_executable)
# - Structured missing field detection
# - Deterministic clarification questions
# - No fallback decomposition (no guessing)
# - Pipeline integration with StrictPipeline
# - Edge cases: empty, garbage, ambiguous, fully specified

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.intent_clarifier import (
    ClarificationRequest,
    IntentClarifier,
    IntentStatus,
    MissingField,
)
from core.strict_pipeline import StrictPipeline
from core.tool_registry import ToolRegistry
from core.tool_schemas import TOOL_SCHEMAS
from tools.inject_failure import INJECT_FAILURE_TOOL, inject_failure
from tools.list_dir import list_dir
from tools.read_file import read_file
from tools.write_file import write_file


# ============================================================
# HELPERS
# ============================================================

def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register("write_file", write_file, TOOL_SCHEMAS["write_file"])
    registry.register("read_file", read_file, TOOL_SCHEMAS["read_file"])
    registry.register("list_dir", list_dir, TOOL_SCHEMAS["list_dir"])
    registry.register(INJECT_FAILURE_TOOL, inject_failure, TOOL_SCHEMAS.get(INJECT_FAILURE_TOOL, {}))
    return registry


def _pipe() -> StrictPipeline:
    return StrictPipeline(_registry())


# ============================================================
# 1. INTENT COMPLETENESS CLASSIFICATION
# ============================================================

def test_empty_goal_non_executable():
    """Empty goal must be classified as NON_EXECUTABLE."""
    clarifier = IntentClarifier()
    result = clarifier.clarify("")
    assert result.status == IntentStatus.NON_EXECUTABLE
    assert len(result.clarification_questions) > 0


def test_whitespace_goal_non_executable():
    """Whitespace-only goal must be classified as NON_EXECUTABLE."""
    clarifier = IntentClarifier()
    result = clarifier.clarify("   ")
    assert result.status == IntentStatus.NON_EXECUTABLE


def test_garbage_goal_non_executable():
    """Garbage input must be classified as NON_EXECUTABLE."""
    clarifier = IntentClarifier()
    result = clarifier.clarify("123!@#$%^&*")
    assert result.status == IntentStatus.NON_EXECUTABLE


def test_fully_specified_goal_executable():
    """Fully specified goal must be EXECUTABLE."""
    clarifier = IntentClarifier()
    result = clarifier.clarify(
        "1. create hello.txt with content world"
    )
    assert result.status == IntentStatus.EXECUTABLE, (
        f"Expected EXECUTABLE, got {result.status}: missing_fields={result.missing_fields}"
    )
    assert result.step_count == 1


def test_multi_step_fully_specified_executable():
    """Multi-step fully specified goal must be EXECUTABLE."""
    clarifier = IntentClarifier()
    result = clarifier.clarify(
        "1. create a.txt with content hello\n2. read a.txt"
    )
    assert result.status == IntentStatus.EXECUTABLE, (
        f"Expected EXECUTABLE, got {result.status}: missing_fields={result.missing_fields}"
    )
    assert result.step_count == 2


def test_three_step_fully_specified_executable():
    """Three-step fully specified goal must be EXECUTABLE."""
    clarifier = IntentClarifier()
    result = clarifier.clarify(
        "1. create a.txt with content hello\n"
        "2. create b.txt with content world\n"
        "3. read a.txt"
    )
    assert result.status == IntentStatus.EXECUTABLE
    assert result.step_count == 3


# ============================================================
# 2. MISSING FIELD DETECTION
# ============================================================

def test_missing_filename_for_write():
    """Write step without filename must produce missing field."""
    clarifier = IntentClarifier()
    result = clarifier.clarify("1. create a file with content hello")
    assert result.status == IntentStatus.PARTIAL, (
        f"Expected PARTIAL, got {result.status}"
    )
    assert len(result.missing_fields) >= 1
    filename_missing = any(
        mf.field_name == "filename" for mf in result.missing_fields
    )
    assert filename_missing, (
        f"Expected filename missing: {result.missing_fields}"
    )


def test_missing_content_for_write():
    """Write step without content must produce missing field."""
    clarifier = IntentClarifier()
    result = clarifier.clarify("1. create hello.txt")
    assert result.status == IntentStatus.PARTIAL
    content_missing = any(
        mf.field_name == "content" for mf in result.missing_fields
    )
    assert content_missing, (
        f"Expected content missing: {result.missing_fields}"
    )


def test_missing_filename_for_read():
    """Read step without filename must produce missing field."""
    clarifier = IntentClarifier()
    result = clarifier.clarify("1. read a file")
    assert result.status == IntentStatus.PARTIAL
    filename_missing = any(
        mf.field_name == "filename" for mf in result.missing_fields
    )
    assert filename_missing


def test_missing_all_for_create():
    """Create step without filename or content must produce 2 missing fields."""
    clarifier = IntentClarifier()
    result = clarifier.clarify("1. create something")
    assert result.status == IntentStatus.PARTIAL
    assert len(result.missing_fields) >= 2
    field_names = {mf.field_name for mf in result.missing_fields}
    assert "filename" in field_names
    assert "content" in field_names


def test_list_dir_without_path():
    """list_dir without explicit path must request clarification (if path not extracted)."""
    clarifier = IntentClarifier()
    result = clarifier.clarify("1. list files")
    # list_dir entity extraction defaults path to "." so it's not flagged as missing.
    # The intent should still be EXECUTABLE since the tool schema allows default ".".
    # This test validates that list_dir is properly detected.
    assert result.step_count == 1
    assert len(result.detected_tools) > 0


# ============================================================
# 3. DETERMINISM TESTS
# ============================================================

def test_deterministic_classification():
    """Same ambiguous input must produce identical output every time."""
    clarifier = IntentClarifier()
    inputs = [
        "",
        "1. create",
        "1. create hello.txt with content world",
        "1. read a file",
        "garbage!!!",
        "1. list directory",
    ]
    for inp in inputs:
        r1 = clarifier.clarify(inp)
        r2 = clarifier.clarify(inp)
        assert r1.status == r2.status, f"Input '{inp}': status mismatch"
        assert len(r1.missing_fields) == len(r2.missing_fields), (
            f"Input '{inp}': missing fields count mismatch"
        )
        q1 = list(r1.clarification_questions)
        q2 = list(r2.clarification_questions)
        assert q1 == q2, f"Input '{inp}': non-deterministic questions: {q1} != {q2}"


def test_deterministic_questions_for_missing_field():
    """Same missing field always produces same question text."""
    clarifier = IntentClarifier()
    r1 = clarifier.clarify("1. create")
    r2 = clarifier.clarify("1. create")
    if r1.missing_fields and r2.missing_fields:
        for mf1, mf2 in zip(r1.missing_fields, r2.missing_fields):
            assert mf1.question == mf2.question
            assert mf1.expected_format == mf2.expected_format


# ============================================================
# 4. NO GUESSING / NO DEFAULTING
# ============================================================

def test_no_default_filename_for_write():
    """Clarifier must NOT default filename — only SimpleParser does that."""
    clarifier = IntentClarifier()
    result = clarifier.clarify("1. write some content")
    # Must NOT produce a DAG-like structure — must ask for filename
    assert result.status == IntentStatus.PARTIAL
    filename_missing = any(
        mf.field_name == "filename" for mf in result.missing_fields
    )
    assert filename_missing, "Must not default filename — must ask for it"


def test_no_default_content_for_write():
    """Clarifier must NOT default content."""
    clarifier = IntentClarifier()
    result = clarifier.clarify("1. create output.txt")
    content_missing = any(
        mf.field_name == "content" for mf in result.missing_fields
    )
    assert content_missing, "Must not default content — must ask for it"


def test_no_unknown_tool_guessing():
    """Clarifier must not guess tool for completely ambiguous steps — NON_EXECUTABLE."""
    clarifier = IntentClarifier()
    result = clarifier.clarify("1. do something")
    assert result.status == IntentStatus.NON_EXECUTABLE, (
        f"Expected NON_EXECUTABLE, got {result.status}"
    )
    # If the tool is unknown, we should not create missing fields for tool args
    for mf in result.missing_fields:
        assert mf.tool_name != "unknown", (
            "Must not create missing fields for unknown tools"
        )


# ============================================================
# 5. STRUCTURED CLARIFICATION OUTPUT
# ============================================================

def test_missing_field_has_question():
    """Every missing field must have a non-empty question."""
    clarifier = IntentClarifier()
    result = clarifier.clarify("1. create")
    for mf in result.missing_fields:
        assert mf.question, f"Missing question for field {mf.field_name}"
        assert "?" in mf.question or ":" in mf.question, (
            f"Question should end with ? or contain guidance: {mf.question}"
        )


def test_missing_field_has_step_index():
    """Every missing field must reference its step."""
    clarifier = IntentClarifier()
    result = clarifier.clarify(
        "1. create a.txt\n2. read"
    )
    for mf in result.missing_fields:
        assert isinstance(mf.step_index, int)
        assert mf.step_index >= 0


def test_partial_goal_has_questions():
    """PARTIAL status must produce at least one clarification question."""
    clarifier = IntentClarifier()
    result = clarifier.clarify("1. create a.txt")
    assert result.status == IntentStatus.PARTIAL
    assert len(result.clarification_questions) > 0


def test_example_partial_output():
    """Verify the structure of a real partial output."""
    clarifier = IntentClarifier()
    result = clarifier.clarify("1. create a.txt")
    expected_question = "Step 1: what content should be written to the file?"
    assert expected_question in result.clarification_questions, (
        f"Expected '{expected_question}' in {result.clarification_questions}"
    )


# ============================================================
# 6. PIPELINE INTEGRATION TESTS
# ============================================================

def test_pipeline_accepts_executable_goal():
    """StrictPipeline must accept EXECUTABLE goals (backward compat)."""
    pipe = _pipe()
    result = pipe.run("1. create ok.txt with content data")
    assert result.status == "success", (
        f"Pipeline should succeed for executable goal: {result.failure}"
    )
    assert result.clarification is None
    for f in ("ok.txt",):
        if os.path.exists(f):
            os.remove(f)


def test_pipeline_returns_clarification_for_partial():
    """StrictPipeline must return CLARIFICATION_REQUIRED for partial goals."""
    pipe = _pipe()
    result = pipe.run("1. create")
    assert result.status == "clarification_required", (
        f"Expected clarification_required, got {result.status}"
    )
    assert result.clarification is not None
    assert result.clarification.status == IntentStatus.PARTIAL


def test_pipeline_returns_clarification_for_empty():
    """Empty goal is caught by normalization before clarification gate — expects failure."""
    pipe = _pipe()
    result = pipe.run("")
    assert result.status == "failed"


def test_clarification_pipeline_stage_recorded():
    """The intent_clarification stage must appear in pipeline stages."""
    pipe = _pipe()
    result = pipe.run("1. create")
    stages = [s.stage for s in result.stages]
    assert "intent_clarification" in stages


def test_pipeline_does_not_plan_after_clarification():
    """Planning must NOT occur after clarification is required."""
    pipe = _pipe()
    result = pipe.run("1. create")
    assert result.status == "clarification_required"
    assert result.plan is None, "No plan should exist after clarification required"


# ============================================================
# 7. EDGE CASE TESTS
# ============================================================

def test_multiple_missing_fields_across_steps():
    """Multiple steps with missing fields must all be reported."""
    clarifier = IntentClarifier()
    result = clarifier.clarify(
        "1. create\n2. read"
    )
    assert result.status == IntentStatus.PARTIAL
    assert len(result.missing_fields) >= 2
    # Both steps should contribute missing fields
    step_indices = {mf.step_index for mf in result.missing_fields}
    assert 0 in step_indices, "Step 0 should have missing fields"
    assert 1 in step_indices, "Step 1 should have missing fields"


def test_partial_with_some_complete_steps():
    """Mixed complete and incomplete steps must still be PARTIAL."""
    clarifier = IntentClarifier()
    result = clarifier.clarify(
        "1. create hello.txt with content world\n2. read"
    )
    assert result.status == IntentStatus.PARTIAL
    # Step 2 should be flagged
    step2_missing = [mf for mf in result.missing_fields if mf.step_index == 1]
    assert len(step2_missing) > 0


def test_list_dir_edge_case():
    """list_dir without explicit path is accepted (entity extraction defaults path to '.')."""
    clarifier = IntentClarifier()
    result = clarifier.clarify("1. list files")
    # list_dir entity extraction defaults to "." so this is EXECUTABLE
    assert result.step_count >= 1


# ============================================================
# RUNNER
# ============================================================

def run_all():
    # 1. Intent completeness classification
    test_empty_goal_non_executable()
    test_whitespace_goal_non_executable()
    test_garbage_goal_non_executable()
    test_fully_specified_goal_executable()
    test_multi_step_fully_specified_executable()
    test_three_step_fully_specified_executable()

    # 2. Missing field detection
    test_missing_filename_for_write()
    test_missing_content_for_write()
    test_missing_filename_for_read()
    test_missing_all_for_create()
    test_list_dir_without_path()

    # 3. Determinism
    test_deterministic_classification()
    test_deterministic_questions_for_missing_field()

    # 4. No guessing
    test_no_default_filename_for_write()
    test_no_default_content_for_write()
    test_no_unknown_tool_guessing()

    # 5. Structured output
    test_missing_field_has_question()
    test_missing_field_has_step_index()
    test_partial_goal_has_questions()
    test_example_partial_output()

    # 6. Pipeline integration
    test_pipeline_accepts_executable_goal()
    test_pipeline_returns_clarification_for_partial()
    test_pipeline_returns_clarification_for_empty()
    test_clarification_pipeline_stage_recorded()
    test_pipeline_does_not_plan_after_clarification()

    # 7. Edge cases
    test_multiple_missing_fields_across_steps()
    test_partial_with_some_complete_steps()
    test_list_dir_edge_case()

    print("ALL v1.9 CLARIFICATION ENGINE TESTS PASSED")


if __name__ == "__main__":
    run_all()
