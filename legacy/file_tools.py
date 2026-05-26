import os

# ====================================================
# WRITE FILE (STRICT CONTRACT)
# ====================================================
def write_file(path: str, content: str = ""):

    if path is None:
        raise ValueError("path cannot be None")

    path = str(path).strip()

    with open(path, "w", encoding="utf-8") as f:
        f.write(content or "")

    return {
        "status": "success",
        "output": {
            "file": path,
            "bytes": len(content or "")
        }
    }


# ====================================================
# READ FILE
# ====================================================
def read_file(path: str):

    if path is None:
        raise ValueError("path cannot be None")

    with open(path, "r", encoding="utf-8") as f:
        data = f.read()

    return {
        "status": "success",
        "output": {
            "file": path,
            "content": data,
            "bytes": len(data)
        }
    }


# ====================================================
# LIST DIRECTORY
# ====================================================
def list_dir(path: str = "."):

    items = os.listdir(path)

    return {
        "status": "success",
        "output": {
            "path": path,
            "items": items,
            "count": len(items)
        }
    }