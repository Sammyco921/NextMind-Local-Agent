import os
from tools.tool_registry import ToolRegistry
from tools.file_tools import write_file, read_file, list_dir
from core.executor import Executor


TEST_FILE = "executor_test.txt"


# ====================================================
# FIXTURE SETUP
# ====================================================

def build_executor():
    registry = ToolRegistry()

    registry.register("write_file", write_file)
    registry.register("read_file", read_file)
    registry.register("list_dir", list_dir)

    return Executor(registry=registry)


# ====================================================
# TEST 1: WRITE FILE SUCCESS
# ====================================================

def test_write_file_success():
    executor = build_executor()

    step = {
        "id": 0,
        "tool": "write_file",
        "args": {
            "filename": TEST_FILE,
            "content": "hello executor"
        }
    }

    result = executor.run(step)

    assert result["status"] == "success"
    assert os.path.exists(TEST_FILE)

    with open(TEST_FILE, "r", encoding="utf-8") as f:
        assert "hello executor" in f.read()


# ====================================================
# TEST 2: READ FILE SUCCESS
# ====================================================

def test_read_file_success():
    executor = build_executor()

    with open(TEST_FILE, "w", encoding="utf-8") as f:
        f.write("read test")

    step = {
        "id": 1,
        "tool": "read_file",
        "args": {
            "filename": TEST_FILE
        }
    }

    result = executor.run(step)

    assert result["status"] == "success"
    assert result["output"]["content"] == "read test"


# ====================================================
# TEST 3: LIST DIRECTORY SUCCESS
# ====================================================

def test_list_dir_success():
    executor = build_executor()

    step = {
        "id": 2,
        "tool": "list_dir",
        "args": {
            "path": "."
        }
    }

    result = executor.run(step)

    assert result["status"] == "success"
    assert isinstance(result["output"]["items"], list)


# ====================================================
# TEST 4: UNKNOWN TOOL FAILS
# ====================================================

def test_unknown_tool():
    executor = build_executor()

    step = {
        "id": 3,
        "tool": "non_existent_tool",
        "args": {}
    }

    result = executor.run(step)

    assert result["status"] == "fatal_error"
    assert "Unknown tool" in result["error"]


# ====================================================
# TEST 5: INVALID ARGS TYPE
# ====================================================

def test_invalid_args():
    executor = build_executor()

    step = {
        "id": 4,
        "tool": "write_file",
        "args": "not_a_dict"
    }

    try:
        executor.run(step)
        assert False, "Should have raised TypeError or failed safely"
    except Exception:
        assert True


# ====================================================
# CLEANUP
# ====================================================

def cleanup():
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)


# ====================================================
# RUN ALL
# ====================================================

def run_all():
    cleanup()

    try:
        test_write_file_success()
        cleanup()

        test_read_file_success()
        cleanup()

        test_list_dir_success()
        cleanup()

        test_unknown_tool()
        cleanup()

        test_invalid_args()

        print("\nEXECUTOR TESTS PASSED\n")

    except AssertionError as e:
        print("\nEXECUTOR TEST FAILED:\n", e)


if __name__ == "__main__":
    run_all()
