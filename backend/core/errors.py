# core/errors.py
#
# Domain-specific error definitions used across the execution runtime.

from __future__ import annotations

from typing import Any


class SpecHashMismatchError(Exception):
    """Raised when an operation's spec hash doesn't match the expected value."""

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        super().__init__(message)


class UnresolvedDependencyError(Exception):
    """Raised when a DAG node's dependencies cannot be resolved."""

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        super().__init__(message)
