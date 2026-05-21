import os

def list_dir(path="."):
    items = os.listdir(path)

    return {
        "status": "success",
        "path": path,
        "items": items,
        "count": len(items)
    }