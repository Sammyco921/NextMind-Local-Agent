# core/artifact_resolver.py
#
# Phase 2: bind unresolved raw_args to runtime artifact values.

from __future__ import annotations

import re
from typing import Any, Dict, List

from core.artifact_refs import REF_MARKER_KEYS, is_unresolved_value
from core.transform_semantics import combine_parts, word_reverse
from core.dag_node import DAGNode
from core.errors import UnresolvedDependencyError
from core.execution_context import ExecutionContext
from core.types import NodeId

_ARTIFACT_OUTPUT_RE = re.compile(r"^(n\d+)\.output$")
_DEPENDENCY_RE = re.compile(r"^dependency\[(n\d+)\]$")


class ArtifactResolver:
    """
    Resolves all raw_args references against context.artifacts before tool execution.
    """

    def resolve_dependencies(
        self,
        dependencies: List[NodeId],
        context: ExecutionContext,
        *,
        node_id: NodeId,
    ) -> None:
        """Ensure every declared dependency already has a stored artifact."""
        for dep_id in dependencies:
            if not context.has_artifact(dep_id):
                raise UnresolvedDependencyError(
                    f"Unresolved dependency: node {node_id} requires artifact "
                    f"from '{dep_id}' but it has not been executed yet"
                )

    def resolve_inputs(
        self,
        node: DAGNode,
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """
        Resolve raw_args to concrete tool arguments.
        Raises UnresolvedDependencyError on missing artifacts or empty resolved values.
        """
        self.resolve_dependencies(node.dependencies, context, node_id=node.node_id)

        resolved: Dict[str, Any] = {}
        for key, value in (node.raw_args or {}).items():
            resolved[key] = self._resolve_value(
                value,
                node=node,
                context=context,
            )

        self._enforce_resolved(node.node_id, resolved)
        return resolved

    def fetch_artifact_field(
        self,
        node_id: NodeId,
        context: ExecutionContext,
        field: str = "content",
    ) -> Any:
        if not context.has_artifact(node_id):
            raise UnresolvedDependencyError(
                f"Unresolved dependency: no artifact for node '{node_id}'"
            )

        artifact = context.get_artifact(node_id)

        if field == "." or field == "output":
            return artifact

        if isinstance(artifact, dict):
            if field not in artifact:
                raise UnresolvedDependencyError(
                    f"Unresolved dependency: artifact '{node_id}' "
                    f"has no field '{field}'"
                )
            value = artifact[field]
        else:
            value = artifact

        if isinstance(value, str) and value.strip() == "":
            raise UnresolvedDependencyError(
                f"Unresolved dependency: artifact '{node_id}.{field}' is empty"
            )

        return value

    def _resolve_value(
        self,
        value: Any,
        *,
        node: DAGNode,
        context: ExecutionContext,
    ) -> Any:
        if isinstance(value, dict):
            return self._resolve_dict(value, node=node, context=context)

        if isinstance(value, list):
            return [
                self._resolve_value(v, node=node, context=context)
                for v in value
            ]

        if isinstance(value, str):
            return self._resolve_string(value, node=node, context=context)

        return value

    def _resolve_dict(
        self,
        value: Dict[str, Any],
        *,
        node: DAGNode,
        context: ExecutionContext,
    ) -> Any:
        # Legacy combine marker
        if "$combine_reverse" in value:
            sources = value.get("$sources")
            if isinstance(sources, list) and sources:
                return self._combine_reverse_from_sources(sources, node, context)
            return self._combine_reverse(node.dependencies, context)

        if "$transform" in value:
            transform = value["$transform"]
            sources = value.get("$sources", [])
            if transform == "combine_reverse":
                return self._combine_reverse_from_sources(sources, node, context)
            if transform == "combine_reverse_words":
                sep = value.get("$separator", " ")
                if not isinstance(sep, str):
                    sep = " "
                return self._combine_reverse_words_from_sources(
                    sources, node, context, separator=sep
                )
            if transform == "combine":
                return self._combine_from_sources(sources, node, context)
            if transform == "reverse":
                source = sources[0] if sources else None
                if source is None:
                    raise UnresolvedDependencyError(
                        f"Unresolved dependency: node {node.node_id} "
                        "reverse transform requires a source artifact"
                    )
                text = str(
                    self._resolve_value(source, node=node, context=context)
                )
                return text[::-1]
            raise UnresolvedDependencyError(
                f"Unresolved dependency: unknown transform '{transform}'"
            )

        if "$artifact" in value or "$ref" in value:
            ref_id = value.get("$artifact") or value.get("$ref")
            if not isinstance(ref_id, str):
                raise UnresolvedDependencyError(
                    "Unresolved dependency: $artifact/$ref must be a node id string"
                )
            field = value.get("$field", value.get("field", "content"))
            return self.fetch_artifact_field(ref_id, context, str(field))

        if "$dependency" in value:
            dep_id = value["$dependency"]
            if not isinstance(dep_id, str):
                raise UnresolvedDependencyError(
                    "Unresolved dependency: $dependency must be a node id string"
                )
            field = value.get("$field", "content")
            return self.fetch_artifact_field(dep_id, context, str(field))

        if "$previous_node" in value:
            return self._resolve_previous_node(node, context, str(value["$previous_node"]))

        # Plain dict: resolve values recursively (no ref keys at top)
        if any(k in REF_MARKER_KEYS for k in value):
            raise UnresolvedDependencyError(
                f"Unresolved dependency: unrecognized reference {value}"
            )

        return {
            k: self._resolve_value(v, node=node, context=context)
            for k, v in value.items()
        }

    def _resolve_string(
        self,
        value: str,
        *,
        node: DAGNode,
        context: ExecutionContext,
    ) -> str:
        if value in ("$previous_node", "previous_node"):
            artifact = self._resolve_previous_node(node, context, "content")
            return str(artifact)

        if value.startswith("$node:"):
            ref_id = value.split(":", 1)[1]
            return str(self.fetch_artifact_field(ref_id, context, "content"))

        match = _ARTIFACT_OUTPUT_RE.match(value)
        if match:
            return str(
                self.fetch_artifact_field(match.group(1), context, "content")
            )

        dep_match = _DEPENDENCY_RE.match(value)
        if dep_match:
            return str(
                self.fetch_artifact_field(dep_match.group(1), context, "content")
            )

        # Literal string (must not be empty — enforced later)
        return value

    def _resolve_previous_node(
        self,
        node: DAGNode,
        context: ExecutionContext,
        field: str,
    ) -> Any:
        if not node.dependencies:
            raise UnresolvedDependencyError(
                f"Unresolved dependency: node {node.node_id} "
                "uses previous_node but has no dependencies"
            )
        dep_id = node.dependencies[-1]
        return self.fetch_artifact_field(dep_id, context, field)

    def _combine_reverse_from_sources(
        self,
        sources: List[Any],
        node: DAGNode,
        context: ExecutionContext,
    ) -> str:
        combined = self._combine_from_sources(sources, node, context)
        return combined[::-1]

    def _combine_reverse_words_from_sources(
        self,
        sources: List[Any],
        node: DAGNode,
        context: ExecutionContext,
        *,
        separator: str = " ",
    ) -> str:
        parts: List[str] = []
        for source in sources:
            part = self._resolve_value(source, node=node, context=context)
            parts.append(str(part))
        combined = combine_parts(parts, separator)
        return word_reverse(combined)

    def _combine_from_sources(
        self,
        sources: List[Any],
        node: DAGNode,
        context: ExecutionContext,
    ) -> str:
        if not sources:
            raise UnresolvedDependencyError(
                f"Unresolved dependency: node {node.node_id} "
                "combine transform requires $sources"
            )
        parts: List[str] = []
        for source in sources:
            part = self._resolve_value(source, node=node, context=context)
            parts.append(str(part))
        return "".join(parts)

    def _combine_reverse(
        self,
        dependencies: List[NodeId],
        context: ExecutionContext,
    ) -> str:
        if not dependencies:
            raise UnresolvedDependencyError(
                "Unresolved dependency: combine_reverse requires dependencies"
            )
        parts: List[str] = []
        for dep_id in dependencies:
            parts.append(
                str(self.fetch_artifact_field(dep_id, context, "content"))
            )
        return "".join(parts)[::-1]

    def _enforce_resolved(self, node_id: NodeId, resolved: Dict[str, Any]) -> None:
        for key, value in resolved.items():
            if is_unresolved_value(value):
                raise UnresolvedDependencyError(
                    f"Unresolved dependency: node {node_id} arg '{key}' "
                    f"still contains an unresolved reference: {value!r}"
                )
            if value == "" or (isinstance(value, str) and value.strip() == ""):
                raise UnresolvedDependencyError(
                    f"Unresolved dependency: node {node_id} arg '{key}' "
                    "resolved to empty string"
                )
