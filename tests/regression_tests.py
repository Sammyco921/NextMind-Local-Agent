import os
import shutil
from main import build_system


TEST_FILE = "test_regression.txt"
TEST_DIR = "."


# ====================================================
# CLEANUP HELPERS
# ====================================================

def cleanup():
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)


# ====================================================
# TEST 1: WRITE FILE
# ====================================================

def test_write_file():
    system = build_system()

    goal = f'create a file called {TEST_FILE} containing "hello regression"'
    result = system.run(goal)

    assert result["status"] == "success", result

    assert os.path.exists(TEST_FILE)

    with open(TEST_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    assert "hello regression" in content


# ====================================================
# TEST 2: READ FILE
# ====================================================

def test_read_file():
    system = build_system()

    with open(TEST_FILE, "w", encoding="utf-8") as f:
        f.write("read me")

    result = system.run(f"read file {TEST_FILE}")

    assert result["status"] == "success", result

    last_output = result["history"][-1]["result"]["output"]
    assert "read me" in last_output["content"]


# ====================================================
# TEST 3: LIST DIRECTORY
# ====================================================

def test_list_dir():
    system = build_system()

    result = system.run("list files in current directory")

    assert result["status"] == "success", result

    last_output = result["history"][-1]["result"]["output"]
    assert isinstance(last_output["items"], list)


# ====================================================
# TEST 4: FAILURE HANDLING (MISSING FILE)
# ====================================================

def test_missing_file():
    system = build_system()

    result = system.run("read file definitely_not_real_123.txt")

    assert result["status"] in ["fail", "fatal_error"]


# ====================================================
# RUN ALL
# ====================================================

def run_all():
    cleanup()

    try:
        test_write_file()
        cleanup()

        test_read_file()
        cleanup()

        test_list_dir()
        cleanup()

        test_missing_file()

        print("\nALL REGRESSION TESTS PASSED\n")

    except AssertionError as e:
        print("\nREGRESSION TEST FAILED:\n", e)


if __name__ == "__main__":
    run_all()
