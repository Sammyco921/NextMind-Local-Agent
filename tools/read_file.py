import os


def read_file(filename: str):
    """
    Deterministic file read tool.
    """

    if not os.path.exists(filename):
        raise FileNotFoundError(f"File not found: {filename}")

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "status": "success",
        "file": filename,
        "content": content,
        "bytes": len(content)
    }