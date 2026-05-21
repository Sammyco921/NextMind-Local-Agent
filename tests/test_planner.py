import re
from core.llm import LLM
from core.planner import Planner
from tools.tool_schemas import TOOL_SCHEMAS


# ====================================================
# FIXTURE
# ====================================================

def build_planner():
    llm = LLM()
    return Planner(llm=llm, tool_schemas=TOOL_SCHEMAS)


# ====================================================
# HELPERS
# ====================================================

def is_valid_step(step):
    return (
        isinstance(step, dict)
        and "tool" in step
        and "args" in step
        and isinstance(step["args"], dict)
    )


def has_empty_strings(step):
    for v in step.get("args", {}).values():
        if v == "":
            return True
    return False


# ====================================================
# TEST 1: BASIC WRITE PLAN
# ====================================================

def test_basic_write_plan():
    planner = build_planner()

    result = planner.create_plan(
        "create a file called test.txt containing hello world"
    )

    assert "steps" in result
    assert len(result["steps"]) > 0

    step = result["steps"][0]

    assert step["tool"] == "write_file"
    assert "filename" in step["args"]
    assert "content" in step["args"]

    assert step["args"]["filename"] != ""
    assert step["args"]["content"] != ""


# ====================================================
# TEST 2: READ FILE PLAN
# ====================================================

def test_read_plan():
    planner = build_planner()

    result = planner.create_plan("read file test.txt")

    step = result["steps"][0]

    assert step["tool"] == "read_file"
    assert "filename" in step["args"]


# ====================================================
# TEST 3: LIST DIRECTORY PLAN
# ====================================================

def test_list_plan():
    planner = build_planner()

    result = planner.create_plan("list files in current directory")

    step = result["steps"][0]

    assert step["tool"] == "list_dir"
    assert "path" in step["args"]


# ====================================================
# TEST 4: STRUCTURE VALIDITY
# ====================================================

def test_structure_validity():
    planner = build_planner()

    result = planner.create_plan("create a file and then read it")

    assert isinstance(result, dict)
    assert "steps" in result

    for step in result["steps"]:
        assert is_valid_step(step)


# ====================================================
# TEST 5: NO EMPTY ARGUMENTS (VERY IMPORTANT FOR YOU)
# ====================================================

def test_no_empty_args():
    planner = build_planner()

    result = planner.create_plan(
        "create a file called test.txt containing banana waffles"
    )

    for step in result["steps"]:
        for k, v in step.get("args", {}).items():
            assert v != "", f"Empty arg found in {step}"


# ====================================================
# TEST 6: MULTI STEP CAPABILITY
# ====================================================

def test_multi_step_output():
    planner = build_planner()

    result = planner.create_plan(
        "create a file test.txt then read it"
    )

    assert isinstance(result["steps"], list)
    assert len(result["steps"]) >= 1

    tools = [s["tool"] for s in result["steps"]]

    assert "write_file" in tools


# ====================================================
# TEST 7: INVALID PROMPT RESILIENCE
# ====================================================

def test_robustness():
    planner = build_planner()

    result = planner.create_plan("do something with files and stuff and things")

    assert isinstance(result, dict)
    assert "steps" in result
    assert isinstance(result["steps"], list)


# ====================================================
# RUN
# ====================================================

def run_all():
    try:
        test_basic_write_plan()
        test_read_plan()
        test_list_plan()
        test_structure_validity()
        test_no_empty_args()
        test_multi_step_output()
        test_robustness()

        print("\nPLANNER TESTS PASSED\n")

    except AssertionError as e:
        print("\nPLANNER TEST FAILED:\n", e)


if __name__ == "__main__":
    run_all()
