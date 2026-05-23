# tools/filesystem_tools.py
#
# NextMind v0.8 — Filesystem Tool Suite
#
# Role:
#   Deterministic, side-effect explicit filesystem operations.
#
# Design rules:
#   - No hidden state
#   - No caching
#   - No interpretation logic
#   - Pure OS interaction wrappers


from __future__ import annotations

import os
from typing import Dict, Any


# =====================================================
# WRITE FILE
# =====================================================

def write_file(filename: str, content: str) -> Dict[str, Any]:
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "file": filename,
        "bytes": len(content),
        "mode": "write"
    }


# =====================================================
# READ FILE
# =====================================================

def read_file(filename: str) -> Dict[str, Any]:
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "file": filename,
        "content": content,
        "bytes": len(content)
    }


# =====================================================
# LIST DIRECTORY
# =====================================================

def list_dir(path: str = ".") -> Dict[str, Any]:
    items = os.listdir(path)

    files = 0
    dirs = 0

    for item in items:
        full = os.path.join(path, item)
        if os.path.isdir(full):
            dirs += 1
        else:
            files += 1

    return {
        "path": path,
        "items": items,
        "counts": {
            "files": files,
            "dirs": dirs
        }
    }


# =====================================================
# APPEND FILE
# =====================================================

def append_file(filename: str, content: str) -> Dict[str, Any]:
    with open(filename, "a", encoding="utf-8") as f:
        f.write(content)

    return {
        "file": filename,
        "bytes_appended": len(content),
        "mode": "append"
    }


# =====================================================
# DELETE FILE
# =====================================================

def delete_file(filename: str) -> Dict[str, Any]:
    if not os.path.exists(filename):
        raise FileNotFoundError(f"{filename} does not exist")

    os.remove(filename)

    return {
        "file": filename,
        "deleted": True
    }


# =====================================================
# COPY FILE
# =====================================================

def copy_file(source: str, destination: str) -> Dict[str, Any]:
    with open(source, "r", encoding="utf-8") as f:
        content = f.read()

    with open(destination, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "source": source,
        "destination": destination,
        "bytes": len(content)
    }


# =====================================================
# FILE EXISTS
# =====================================================

def file_exists(filename: str) -> Dict[str, Any]:
    return {
        "file": filename,
        "exists": os.path.exists(filename)
    }


# =====================================================
# SEARCH TEXT IN FILE
# =====================================================

def search_text_in_file(filename: str, query: str) -> Dict[str, Any]:
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    matches = query in content

    return {
        "file": filename,
        "query": query,
        "matches": matches
    }


# =====================================================
# HASH FILE
# =====================================================

def hash_file(filename: str) -> Dict[str, Any]:
    import hashlib

    with open(filename, "rb") as f:
        data = f.read()

    return {
        "file": filename,
        "sha256": hashlib.sha256(data).hexdigest()
    }