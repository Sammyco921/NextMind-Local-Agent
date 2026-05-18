import os
import pytest

from tools.file_tools import write_file, read_file, list_dir


TEST_FILE = "tool_test_file.txt"


# ====================================================
# CLEANUP
# ====================================================

def cleanup():
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)


# ====================================================
# TEST 1: WRITE FILE
# ====================================================

def test_write_file():
    cleanup()

    result = write_file(TEST_FILE, "hello tools")

    assert isinstance(result, dict)
    assert result["file"] == TEST_FILE
    assert result["status"] == "written"
    assert os.path.exists(TEST_FILE)

    with open(TEST_FILE, "r", encoding="utf-8") as f:
        assert f.read() == "hello tools"


# ====================================================
# TEST 2: READ FILE
# ====================================================

def test_read_file():
    cleanup()

    write_file(TEST_FILE, "read test")

    result = read_file(TEST_FILE)

    assert isinstance(result, dict)
    assert result["file"] == TEST_FILE
    assert result["status"] == "read"
    assert "content" in result
    assert result["content"] == "read test"


# ====================================================
# TEST 3: LIST DIRECTORY
# ====================================================

def test_list_dir():
    cleanup()

    write_file(TEST_FILE, "dir test")

    result = list_dir(".")

    assert isinstance(result, dict)
    assert "items" in result
    assert TEST_FILE in result["items"]


# ====================================================
# TEST 4: WRITE INVALID INPUTS (SAFETY CHECK)
# ====================================================

def test_write_invalid_inputs():
    with pytest.raises(ValueError):
        write_file("", "content")

    with pytest.raises(ValueError):
        write_file(TEST_FILE, None)


# ====================================================
# TEST 5: READ MISSING FILE (EXPECTED FAILURE)
# ====================================================

def test_read_missing_file():
    cleanup()

    with pytest.raises(FileNotFoundError):
        read_file("this_file_should_not_exist_123.txt")


# ====================================================
# TEST 6: LIST DIR INVALID PATH
# ====================================================

def test_list_invalid_path():
    with pytest.raises(FileNotFoundError):
        list_dir("/this/path/does/not/exist/123")


# ====================================================
# RUNNER
# ====================================================

def run_all():
    try:
        test_write_file()
        cleanup()

        test_read_file()
        cleanup()

        test_list_dir()
        cleanup()

        test_write_invalid_inputs()
        test_read_missing_file()
        test_list_invalid_path()

        print("\nTOOL TESTS PASSED\n")

    except AssertionError as e:
        print("\nTOOL TEST FAILED:\n", e)


if __name__ == "__main__":
    run_all()
