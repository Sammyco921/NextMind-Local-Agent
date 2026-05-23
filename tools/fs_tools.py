import os


def list_dir(path="."):

    items = os.listdir(path)

    return {
        "path": path,
        "items": items,
        "count": len(items)
    }


def write_file(filename, content):

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "file": filename,
        "status": "written",
        "bytes": len(content)
    }


def read_file(filename):

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "file": filename,
        "content": content,
        "status": "read",
        "bytes": len(content)
    }