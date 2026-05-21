import os
from main import build_system


TEST_FILE = "orch_test.txt"


# ====================================================
# CLEANUP
# ====================================================

def cleanup():
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)


# ====================================================
# TEST 1: SIMPLE SUCCESS FLOW (WRITE)
# ====================================================

def test_success_write_flow():
    system = build_system()

    result = system.run(f'create a file called {TEST_FILE} containing "orchestrator test"')

    assert result["status"] == "success"
    assert os.path.exists(TEST_FILE)

    with open(TEST_FILE, "r", encoding="utf-8") as f:
        assert "orchestrator test" in f.read()


# ====================================================
# TEST 2: LOOP TERMINATION GUARANTEE
# ====================================================

def test_termination():
    system = build_system()

    result = system.run("create something vague and uncertain")

    assert isinstance(result, dict)
    assert "status" in result

    # must always terminate
    assert result["status"] in ["success", "fail", "fatal_error"]


# ====================================================
# TEST 3: REPEATED STEP DETECTION
# ====================================================

def test_repeated_step_breaks_loop():
    system = build_system()

    # This prompt often causes planner repetition
    result = system.run(f'create a file called {TEST_FILE} containing "repeat test"')

    assert isinstance(result, dict)

    # even if success, system must not infinite loop
    assert result["steps_executed"] <= system.max_steps


# ====================================================
# TEST 4: FAILURE LIMIT ENFORCEMENT
# ====================================================

def test_failure_limit():
    system = build_system()

    # guaranteed failure (invalid file path)
    result = system.run("read file /this/path/does/not/exist/definitely.txt")

    assert result["status"] in ["fail", "fatal_error"]

    # must stop within bounds
    assert result["steps_executed"] <= system.max_steps


# ====================================================
# TEST 5: STATE INTEGRITY ACROSS STEPS
# ====================================================

def test_history_consistency():
    system = build_system()

    result = system.run(f'create a file called {TEST_FILE} containing "history test"')

    assert result["status"] in ["success", "fail", "fatal_error"]

    history = result["history"]

    # every history entry must be valid
    for entry in history:
        assert "step" in entry
        assert "result" in entry
        assert isinstance(entry["step"], dict)
        assert isinstance(entry["result"], dict)


# ====================================================
# TEST 6: NO CRASH GUARANTEE
# ====================================================

def test_no_crash():
    system = build_system()

    try:
        result = system.run("do something impossible with files and memory and logic")

        assert isinstance(result, dict)
        assert "status" in result

    except Exception as e:
        assert False, f"System should never crash: {e}"


# ====================================================
# RUN ALL
# ====================================================

def run_all():
    cleanup()

    try:
        test_success_write_flow()
        cleanup()

        test_termination()
        cleanup()

        test_repeated_step_breaks_loop()
        cleanup()

        test_failure_limit()
        cleanup()

        test_history_consistency()
        cleanup()

        test_no_crash()

        print("\nORCHESTRATOR TESTS PASSED\n")

    except AssertionError as e:
        print("\nORCHESTRATOR TEST FAILED:\n", e)


if __name__ == "__main__":
    run_all()
