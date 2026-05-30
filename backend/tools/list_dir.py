import os


def list_dir(path: str = "."):
    """
    Deterministic directory listing tool.
    """

    if not os.path.exists(path):
        raise FileNotFoundError(f"Directory not found: {path}")

    items = os.listdir(path)

    return {
        "status": "success",
        "path": path,
        "items": items,
        "count": len(items)
    }