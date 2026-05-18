import os


# ====================================================
# WRITE FILE (STRICT + SAFE)
# ====================================================

def write_file(filename: str, content: str):

    if not isinstance(filename, str):
        raise ValueError("filename must be a string")

    if not isinstance(content, str):
        raise ValueError("content must be a string")

    filename = filename.strip()

    if filename == "":
        raise ValueError("filename cannot be empty")

    # prevent accidental directory traversal weirdness
    if ".." in filename:
        raise ValueError("invalid filename path")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "file": filename,
        "status": "written",
        "bytes": len(content)
    }


# ====================================================
# READ FILE (STRICT + SAFE)
# ====================================================

def read_file(filename: str):

    if not isinstance(filename, str):
        raise ValueError("filename must be a string")

    filename = filename.strip()

    if filename == "":
        raise ValueError("filename cannot be empty")

    if ".." in filename:
        raise ValueError("invalid filename path")

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
# LIST DIRECTORY (STRICT + CLEAN OUTPUT)
# ====================================================

def list_dir(path="."):

    if not isinstance(path, str):
        raise ValueError("path must be a string")

    path = path.strip()

    if path == "":
        path = "."

    if not os.path.exists(path):
        raise FileNotFoundError(f"Path not found: {path}")

    items = os.listdir(path)

    return {
        "path": path,
        "items": sorted(items),
        "count": len(items)
    }
