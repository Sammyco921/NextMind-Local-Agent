import os
from main import build_system


TEST_FILE = "integration_test.txt"


# ====================================================
# CLEANUP
# ====================================================

def cleanup():
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)


# ====================================================
# TEST 1: SIMPLE WRITE FLOW
# ====================================================

def test_write_flow():
    system = build_system()

    goal = f'create a file called {TEST_FILE} containing "hello integration"'
    result = system.run(goal)

    assert result["status"] == "success"
    assert os.path.exists(TEST_FILE)

    with open(TEST_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    assert "hello integration" in content


# ====================================================
# TEST 2: READ AFTER WRITE (STATE CONSISTENCY)
# ====================================================

def test_read_after_write():
    system = build_system()

    # create file first via system
    system.run(f'create a file called {TEST_FILE} containing "integrated read test"')

    # now read via system
    result = system.run(f"read file {TEST_FILE}")

    assert result["status"] == "success"

    output = result["history"][-1]["result"]["output"]
    assert "integrated read test" in output["content"]


# ====================================================
# TEST 3: DIRECTORY INCLUDES CREATED FILE
# ====================================================

def test_list_includes_file():
    system = build_system()

    system.run(f'create a file called {TEST_FILE} containing "dir test"')

    result = system.run("list files in current directory")

    assert result["status"] == "success"

    items = result["history"][-1]["result"]["output"]["items"]

    assert TEST_FILE in items


# ====================================================
# TEST 4: FAILURE DOES NOT CRASH SYSTEM
# ====================================================

def test_missing_file_handling():
    system = build_system()

    result = system.run("read file this_file_should_not_exist_123.txt")

    assert result["status"] in ["fail", "fatal_error"]

    # system must still remain usable
    follow_up = system.run(f'create a file called {TEST_FILE} containing "recovery test"')

    assert follow_up["status"] == "success"


# ====================================================
# TEST 5: LOOP SAFETY (NO INFINITE LOOP BEHAVIOR)
# ====================================================

def test_no_infinite_loop():
    system = build_system()

    # intentionally ambiguous goal that may confuse planner
    result = system.run("keep doing something with files")

    assert isinstance(result, dict)

    # must terminate
    assert "status" in result


# ====================================================
# RUN
# ====================================================

def run_all():
    cleanup()

    try:
        test_write_flow()
        cleanup()

        test_read_after_write()
        cleanup()

        test_list_includes_file()
        cleanup()

        test_missing_file_handling()
        cleanup()

        test_no_infinite_loop()

        print("\nINTEGRATION TESTS PASSED\n")

    except AssertionError as e:
        print("\nINTEGRATION TEST FAILED:\n", e)


if __name__ == "__main__":
    run_all()
