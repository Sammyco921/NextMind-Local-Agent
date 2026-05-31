from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from typing import Dict, List, Optional


_EXCLUDED_DIRS = frozenset({
    ".git", "__pycache__", ".pytest_cache", "node_modules",
    ".DS_Store", ".eggs", "egg-info", ".tox", "venv", ".venv",
})

_EXCLUDED_FILES = frozenset({".DS_Store"})


@dataclass(frozen=True)
class FileRecord:
    path: str
    dir_path: str
    extension: str
    size: int
    modified_at: str
    is_directory: bool = False


class ProjectCatalog:
    """Deterministic structural inventory of project files and directories.

    Scans the filesystem and records facts only:
    - file path, directory path, extension, size, last modification timestamp
    - directory paths

    Does NOT parse source code, infer architecture, inspect semantics,
    classify purpose, or determine importance.
    """

    def __init__(self, root_path: Optional[str] = None) -> None:
        self._root = root_path or os.getcwd()
        self._files: List[FileRecord] = []
        self._directories: List[str] = []
        self._scanned = False

    def scan(self) -> None:
        self._files = []
        self._directories = []
        seen_dirs: set = set()

        for dirpath, dirnames, filenames in os.walk(self._root):
            rel_dir = os.path.relpath(dirpath, self._root)
            if rel_dir == ".":
                rel_dir = ""

            dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS]

            if rel_dir and rel_dir not in seen_dirs:
                seen_dirs.add(rel_dir)
                self._directories.append(rel_dir)

            for fname in sorted(filenames):
                if fname in _EXCLUDED_FILES:
                    continue
                full = os.path.join(dirpath, fname)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                rel = os.path.join(rel_dir, fname) if rel_dir else fname
                _, ext = os.path.splitext(fname)
                self._files.append(FileRecord(
                    path=rel,
                    dir_path=rel_dir,
                    extension=ext.lower() if ext else "",
                    size=st.st_size,
                    modified_at=_format_time(st.st_mtime),
                ))

        self._files.sort(key=lambda r: r.path)
        self._directories.sort()
        self._scanned = True

    def get_files(self) -> List[FileRecord]:
        if not self._scanned:
            self.scan()
        return list(self._files)

    def get_directories(self) -> List[str]:
        if not self._scanned:
            self.scan()
        return list(self._directories)

    def get_by_extension(self, ext: str) -> List[FileRecord]:
        return [f for f in self.get_files() if f.extension == ext.lower()]

    def get_by_directory(self, dir_path: str) -> List[FileRecord]:
        prefix = dir_path.rstrip("/") + "/"
        return [f for f in self.get_files() if f.path.startswith(prefix) or f.dir_path == dir_path]

    def get_recently_modified(self, count: int = 10) -> List[FileRecord]:
        sorted_by_time = sorted(self.get_files(), key=lambda r: r.modified_at, reverse=True)
        return sorted_by_time[:count]

    def get_file_count(self) -> int:
        return len(self.get_files())

    def get_directory_count(self) -> int:
        return len(self.get_directories())

    def get_extension_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for f in self.get_files():
            ext = f.extension or "(no extension)"
            counts[ext] = counts.get(ext, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))


def _format_time(mtime: float) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
