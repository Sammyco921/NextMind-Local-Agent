# core/artifact_refs.py
#
# Canonical unresolved reference markers (planning phase only).

from __future__ import annotations

import re
from typing import Any, Dict, List

from core.types import NodeId

# Dict keys that mark unresolved values (must not reach tools verbatim)
REF_MARKER_KEYS = frozenset({
    "$artifact",
    "$ref",
    "$field",
    "$transform",
    "$sources",
    "$combine_reverse",
    "$dependency",
    "$previous_node",
})

_ARTIFACT_OUTPUT_RE = re.compile(r"^(n\d+)\.output$")
_DEPENDENCY_RE = re.compile(r"^dependency\[(n\d+)\]$")


def artifact_ref(node_id: NodeId, field: str = "content") -> Dict[str, str]:
    """Explicit reference to a field on a prior node's artifact."""
    return {"$artifact": node_id, "$field": field}


def combine_reverse_sources(read_node_ids: List[NodeId]) -> Dict[str, Any]:
    """Reference combining and reversing content from read node artifacts (char-level)."""
    return {
        "$transform": "combine_reverse",
        "$sources": [artifact_ref(nid) for nid in read_node_ids],
    }


def combine_reverse_words_sources(
    read_node_ids: List[NodeId],
    *,
    separator: str = " ",
) -> Dict[str, Any]:
    """Combine sources then reverse word order (not character order)."""
    return {
        "$transform": "combine_reverse_words",
        "$separator": separator,
        "$sources": [artifact_ref(nid) for nid in read_node_ids],
    }


def is_unresolved_value(value: Any) -> bool:
    """Return True if value still requires artifact resolution."""
    if isinstance(value, str):
        if value in ("$previous_node", "previous_node"):
            return True
        if value.startswith("$node:"):
            return True
        if _ARTIFACT_OUTPUT_RE.match(value):
            return True
        if _DEPENDENCY_RE.match(value):
            return True
        return False

    if isinstance(value, dict):
        if any(k in REF_MARKER_KEYS for k in value):
            return True
        return any(is_unresolved_value(v) for v in value.values())

    if isinstance(value, list):
        return any(is_unresolved_value(v) for v in value)

    return False


def static_placeholder_for_validation(value: Any) -> Any:
    """Replace unresolved refs with valid placeholders for pre-execution validation."""
    if is_unresolved_value(value):
        return "resolved_at_runtime"
    if isinstance(value, dict):
        return {k: static_placeholder_for_validation(v) for k, v in value.items()}
    if isinstance(value, list):
        return [static_placeholder_for_validation(v) for v in value]
    return value
