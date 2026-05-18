import os


def write_file(filename: str, content: str):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "file": filename,
        "status": "written",
        "bytes": len(content)
    }


def read_file(filename: str):
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "file": filename,
        "content": content,
        "status": "read",
        "bytes": len(content)
    }


def list_dir():
    items = os.listdir(".")
    return {
        "path": ".",
        "items": items,
        "count": len(items)
    }