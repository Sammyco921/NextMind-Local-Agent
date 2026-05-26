import os


def write_file(filename: str, content: str):
    """
    Deterministic file write tool.
    Creates parent directories if needed.
    """

    parent = os.path.dirname(filename)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "status": "success",
        "file": filename,
        "bytes": len(content)
    }