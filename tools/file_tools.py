import os


# ====================================================
# WRITE FILE
# ====================================================

def write_file(filename: str, content: str):

    if not isinstance(filename, str) or not filename:
        raise ValueError("filename must be a non-empty string")

    if not isinstance(content, str):
        raise ValueError("content must be a string")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "file": filename,
        "status": "written",
        "bytes": len(content)
    }


# ====================================================
# READ FILE
# ====================================================

def read_file(filename: str):

    if not isinstance(filename, str) or not filename:
        raise ValueError("filename must be a non-empty string")

    if not os.path.exists(filename):
        raise FileNotFoundError(f"File not found: {filename}")

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "file": filename,
        "content": content,
        "status": "read",
        "bytes": len(content)
    }


# ====================================================
# LIST DIRECTORY
# ====================================================

def list_dir(path="."):

    if not isinstance(path, str):
        raise ValueError("path must be a string")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Path not found: {path}")

    items = os.listdir(path)

    return {
        "path": path,
        "items": items,
        "count": len(items)
    }
