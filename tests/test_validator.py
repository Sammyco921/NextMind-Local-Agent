import pytest

from tools.tool_schemas import validate_tool_call


# ====================================================
# TEST 1: VALID WRITE FILE CALL
# ====================================================

def test_valid_write_file():
    assert validate_tool_call(
        "write_file",
        {"filename": "test.txt", "content": "hello"}
    ) is True


# ====================================================
# TEST 2: VALID READ FILE CALL
# ====================================================

def test_valid_read_file():
    assert validate_tool_call(
        "read_file",
        {"filename": "test.txt"}
    ) is True


# ====================================================
# TEST 3: VALID LIST DIR CALL
# ====================================================

def test_valid_list_dir():
    assert validate_tool_call(
        "list_dir",
        {"path": "."}
    ) is True


# ====================================================
# TEST 4: MISSING REQUIRED ARG
# ====================================================

def test_missing_required_arg():
    with pytest.raises(ValueError):
        validate_tool_call(
            "write_file",
            {"filename": "test.txt"}  # missing content
        )


# ====================================================
# TEST 5: EMPTY STRING REJECTION (IMPORTANT FOR YOUR SYSTEM)
# ====================================================

def test_empty_string_rejected():
    with pytest.raises(ValueError):
        validate_tool_call(
            "write_file",
            {"filename": "", "content": "hello"}
        )


# ====================================================
# TEST 6: UNKNOWN TOOL
# ====================================================

def test_unknown_tool():
    with pytest.raises(ValueError):
        validate_tool_call(
            "delete_universe",
            {"foo": "bar"}
        )


# ====================================================
# TEST 7: UNEXPECTED ARG REJECTION
# ====================================================

def test_unexpected_argument():
    with pytest.raises(ValueError):
        validate_tool_call(
            "write_file",
            {
                "filename": "test.txt",
                "content": "hello",
                "extra": "not_allowed"
            }
        )


# ====================================================
# TEST 8: WRONG TYPE INPUT
# ====================================================

def test_wrong_args_type():
    with pytest.raises(ValueError):
        validate_tool_call(
            "write_file",
            "not_a_dict"
        )


# ====================================================
# RUNNER
# ====================================================

def run_all():
    try:
        test_valid_write_file()
        test_valid_read_file()
        test_valid_list_dir()

        test_missing_required_arg()
        test_empty_string_rejected()
        test_unknown_tool()
        test_unexpected_argument()
        test_wrong_args_type()

        print("\nVALIDATOR TESTS PASSED\n")

    except AssertionError as e:
        print("\nVALIDATOR TEST FAILED:\n", e)


if __name__ == "__main__":
    run_all()
