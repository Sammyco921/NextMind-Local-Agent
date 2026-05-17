from typing import Dict, Any
import os


# ----------------------------------------------------
# WRITE FILE
# ----------------------------------------------------
def write_file(filename: str, content: str) -> Dict[str, Any]:
    """
    Writes content to a file.
    """

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "file": filename,
        "status": "written",
        "bytes": len(content)
    }


# ----------------------------------------------------
# READ FILE
# ----------------------------------------------------
def read_file(filename: str) -> Dict[str, Any]:
    """
    Reads content from a file.
    """

    if not os.path.exists(filename):
        raise FileNotFoundError(f"{filename} does not exist")

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "file": filename,
        "content": content,
        "bytes": len(content)
    }


# ----------------------------------------------------
# LIST DIRECTORY
# ----------------------------------------------------
def list_dir() -> Dict[str, Any]:
    """
    Lists current directory contents.
    """

    items = os.listdir(".")

    return {
        "items": items,
        "count": len(items)
    }
