import os
from main import build_system


# ====================================================
# TEST CONFIG
# ====================================================

TEST_FILE = "test_regression.txt"

SYSTEM = build_system()  # reuse single system instance


# ====================================================
# CLEANUP HELPERS
# ====================================================

def cleanup():
    for f in [
        TEST_FILE,
        "notes.txt",
        "test.txt",
        "hello.txt",
        "readme_test.txt"
    ]:
        if os.path.exists(f):
            os.remove(f)


# ====================================================
# SAFE OUTPUT ACCESSOR
# ====================================================

def get_last_output(result):
    """
    Safely extracts last tool output without assuming strict schema.
    Prevents KeyError crashes when orchestrator evolves.
    """

    history = result.get("history", [])
    if not history:
        return {}

    last = history[-1]
    return last.get("result", {}).get("output", {}) or {}


# ====================================================
# TEST 1: WRITE FILE
# ====================================================

def test_write_file():
    system = SYSTEM

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
    system = SYSTEM

    with open(TEST_FILE, "w", encoding="utf-8") as f:
        f.write("read me")

    result = system.run(f"read file {TEST_FILE}")

    assert result["status"] == "success", result

    output = get_last_output(result)

    assert "content" in output
    assert "read me" in output["content"]


# ====================================================
# TEST 3: LIST DIRECTORY
# ====================================================

def test_list_dir():
    system = SYSTEM

    result = system.run("list files in current directory")

    assert result["status"] == "success", result

    output = get_last_output(result)

    assert isinstance(output.get("items", []), list)


# ====================================================
# TEST 4: FAILURE HANDLING
# ====================================================

def test_missing_file():
    system = SYSTEM

    result = system.run("read file definitely_not_real_123.txt")

    assert result["status"] in ["fail", "fatal_error"], result


# ====================================================
# RUN ALL TESTS
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