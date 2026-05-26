# core/artifact_types.py
#
# v1.4 formal artifact type definitions.
# Immutable enum + dataclass — single source of truth for all typed artifacts.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ArtifactType(Enum):
    """Canonical artifact type registry. Immutable after definition."""

    TEXT = "text"
    FILE = "file"
    JSON = "json"
    DIRECTORY = "directory"
    COMMAND_RESULT = "command_result"
    BINARY = "binary"
    IMAGE = "image"
    TABLE = "table"
    BOOLEAN = "boolean"
    NUMBER = "number"
    NULL = "null"

    # Legacy transform support — explicit conversion artifacts
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Artifact:
    """Typed execution artifact. Immutable after creation."""

    type: ArtifactType
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def text(cls, value: str, **metadata: Any) -> Artifact:
        return cls(type=ArtifactType.TEXT, value=value, metadata=metadata)

    @classmethod
    def file(cls, filename: str, content: str = "") -> Artifact:
        return cls(
            type=ArtifactType.FILE,
            value={"filename": filename, "content": content},
            metadata={"filename": filename},
        )

    @classmethod
    def json(cls, value: Any) -> Artifact:
        return cls(type=ArtifactType.JSON, value=value)

    @classmethod
    def directory(cls, path: str, items: list[str] | None = None) -> Artifact:
        return cls(
            type=ArtifactType.DIRECTORY,
            value={"path": path, "items": items or []},
            metadata={"path": path},
        )

    @classmethod
    def null(cls) -> Artifact:
        return cls(type=ArtifactType.NULL, value=None)
