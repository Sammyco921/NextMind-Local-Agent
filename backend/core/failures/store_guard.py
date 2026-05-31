"""Safe wrappers for store persistence operations.

All functions return empty-but-valid defaults on any failure.
The system never crashes from corrupted or missing store data.
"""
import json
import os

from .taxonomy import FailureRecord
from .normalizer import normalize_exception, safe_message_for_file


def safe_json_load(filepath: str, default: dict | list | None = None) -> dict | list:
    """Load JSON, returning default on any failure. Never raises."""
    if default is None:
        default = {}
    try:
        if not os.path.isfile(filepath):
            return default
        with open(filepath, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError, OSError):
        return default


def safe_json_dump(data, filepath: str) -> FailureRecord | None:
    """Write JSON, returning a FailureRecord on failure or None on success."""
    try:
        with open(filepath, "w") as f:
            json.dump(data, f)
        return None
    except (OSError, PermissionError, TypeError) as exc:
        return normalize_exception(exc, "store_guard")


def safe_jsonl_iterate(filepath: str):
    """Yield parsed JSON lines. On any failure, yield nothing silently."""
    try:
        if not os.path.isfile(filepath):
            return
        with open(filepath, "r") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    yield json.loads(stripped)
                except json.JSONDecodeError:
                    continue
    except (FileNotFoundError, PermissionError, OSError):
        return


def safe_jsonl_append(entry: dict, filepath: str) -> FailureRecord | None:
    """Append a JSON line, returning a FailureRecord on failure or None."""
    try:
        with open(filepath, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return None
    except (OSError, PermissionError, TypeError) as exc:
        return normalize_exception(exc, "store_guard")


def safe_markdown_export(text: str, filepath: str) -> FailureRecord | None:
    """Write markdown, returning a FailureRecord on failure or None."""
    try:
        with open(filepath, "w") as f:
            f.write(text)
        return None
    except (OSError, PermissionError, TypeError) as exc:
        return normalize_exception(exc, "store_guard")


def safe_file_read(filepath: str, default: str = "") -> str:
    """Read a text file, returning default on any failure."""
    try:
        if not os.path.isfile(filepath):
            return default
        with open(filepath, "r") as f:
            return f.read()
    except (FileNotFoundError, PermissionError, OSError):
        return default


def safe_dir_list(dirpath: str, default: list | None = None) -> list:
    """List directory entries, returning default on failure."""
    if default is None:
        default = []
    try:
        if not os.path.isdir(dirpath):
            return default
        return sorted(os.listdir(dirpath))
    except (FileNotFoundError, PermissionError, OSError):
        return default
