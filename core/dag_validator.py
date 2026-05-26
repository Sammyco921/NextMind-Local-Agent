# core/dag_validator.py
#
# This validator enforces ONLY structural correctness of directed acyclic graphs.
# It does not evaluate quality, design, efficiency, or semantic correctness of workflows.
#
# ================================================================
# ARCHITECTURAL RULE: Validation must not encode system knowledge
# across executions. It is not a learning system.
# ================================================================
#
# INVARIANTS:
#   - Validator is stateless: DAG → validation result only
#   - No component may depend on previous executions
#   - Identical input must always produce identical validation outcome
#   - No caches, no history, no global mutation, no persistence across runs
#
# FORMAL GRAPH CORRECTNESS ONLY:
#   - DAG is acyclic (no cycles)
#   - All node_id references exist
#   - All dependency targets exist in DAG
#   - No self-dependencies
#   - No duplicate node_ids
#   - Tool exists in registry (schema-level validity)
#   - Tool args conform to schema
#   - No unresolved artifact references
#   - No missing required fields (node_id, tool_name, raw_args)
#   - Topological ordering is valid and complete

from __future__ import annotations

from typing import Any, Dict, List, Set

from core.artifact_refs import is_unresolved_value, static_placeholder_for_validation
from core.dag_node import DAG
from core.planning_errors import PLANNING_ERROR_TOOL
from core.tool_contracts import get_contract
from core.tool_registry import ToolRegistry
from core.tool_schemas import validate_tool_call
from core.type_validator import validate_type_flow


class DAGValidator:
    """Pure graph correctness checker for directed acyclic graphs.
    
    Enforces ONLY structural correctness invariants — no semantic,
    stylistic, or policy-based validation. Fully stateless.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def validate(self, dag: DAG) -> Dict[str, Any]:
        errors: List[str] = []
        nodes = dag.nodes

        if not nodes:
            return {"status": "invalid", "errors": ["DAG contains no nodes"]}

        seen_ids: Set[str] = set()

        for node in nodes:
            node_id = node.node_id
            tool_name = node.tool_name
            raw_args = node.raw_args
            dependencies = node.dependencies

            if not node_id:
                errors.append("Node missing node_id")

            if not tool_name:
                errors.append(f"Node {node_id}: missing tool_name")

            if raw_args is None:
                errors.append(f"Node {node_id}: missing raw_args")

            if dependencies is None:
                errors.append(f"Node {node_id}: missing dependencies")

            if node_id in seen_ids:
                errors.append(f"Duplicate node_id detected: {node_id}")
            else:
                seen_ids.add(node_id)

            if tool_name and not self.registry.has(tool_name):
                errors.append(f"Unknown tool: {tool_name}")

            if tool_name and self.registry.has(tool_name) and raw_args is not None:
                static_args = self._static_args_for_validation(raw_args)
                result = validate_tool_call(tool_name, static_args)
                if result["status"] != "success":
                    errors.append(
                        f"Tool '{tool_name}' arg error: {result.get('reason')}"
                    )

                for key, value in raw_args.items():
                    if not is_unresolved_value(value):
                        if value == "" or (
                            isinstance(value, str) and value.strip() == ""
                        ):
                            errors.append(
                                f"Node {node_id}: arg '{key}' is empty "
                                "(must be literal or artifact reference)"
                            )

            if tool_name and str(tool_name).startswith("legacy"):
                errors.append(f"Blocked legacy tool usage in DAG: {tool_name}")

            if tool_name == PLANNING_ERROR_TOOL:
                msg = (raw_args or {}).get("message", "planning failed")
                errors.append(f"Planning error node present: {msg}")

        valid_ids = {n.node_id for n in nodes}

        for node in nodes:
            for dep in node.dependencies:
                if dep not in valid_ids:
                    errors.append(
                        f"Node {node.node_id} has invalid dependency: {dep}"
                    )
                if dep == node.node_id:
                    errors.append(
                        f"Node {node.node_id} cannot depend on itself"
                    )

            for key, value in (node.raw_args or {}).items():
                for ref_id in self._extract_artifact_refs(value):
                    if ref_id not in valid_ids:
                        errors.append(
                            f"Node {node.node_id}: arg '{key}' references "
                            f"unknown node '{ref_id}'"
                        )
                    elif ref_id not in node.dependencies:
                        errors.append(
                            f"Node {node.node_id}: arg '{key}' references "
                            f"'{ref_id}' but it is not in dependencies"
                        )

        errors.extend(self._validate_dag_topology(nodes))
        errors.extend(validate_type_flow(dag, get_contract))

        if errors:
            return {"status": "invalid", "errors": errors}

        return {"status": "valid", "errors": []}

    def _validate_dag_topology(self, nodes: List) -> List[str]:
        """Cycles, orphans, and full connectivity (v1.9 hard gate)."""
        errors: List[str] = []
        if not nodes:
            return errors

        valid_ids = {n.node_id for n in nodes}
        children: Dict[str, List[str]] = {n.node_id: [] for n in nodes}
        for node in nodes:
            for dep in node.dependencies or []:
                children.setdefault(dep, []).append(node.node_id)

        cycle = self._find_cycle(valid_ids, {n.node_id: list(n.dependencies) for n in nodes})
        if cycle:
            errors.append(f"Circular dependency detected: {' -> '.join(cycle)}")

        roots = [n.node_id for n in nodes if not n.dependencies]
        if not roots:
            errors.append("DAG has no root nodes (every node has a dependency)")

        reachable: Set[str] = set()
        queue = list(roots)
        while queue:
            cur = queue.pop(0)
            if cur in reachable:
                continue
            reachable.add(cur)
            queue.extend(children.get(cur, []))

        for node in nodes:
            if node.node_id not in reachable:
                errors.append(f"Orphan node (not reachable from roots): {node.node_id}")

        if len(reachable) != len(nodes):
            errors.append("DAG is not fully connected from root nodes")

        for i, node in enumerate(nodes):
            for dep in node.dependencies or []:
                dep_node = next((n for n in nodes if n.node_id == dep), None)
                if dep_node is None:
                    continue
                dep_index = nodes.index(dep_node)
                if dep_index >= i:
                    errors.append(
                        f"Implicit ordering violation: node {node.node_id} "
                        f"depends on {dep} which is not earlier in explicit DAG order"
                    )

        return errors

    @staticmethod
    def _find_cycle(
        valid_ids: Set[str],
        adj: Dict[str, List[str]],
    ) -> List[str]:
        visited: Set[str] = set()
        stack: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> List[str]:
            visited.add(node)
            stack.add(node)
            path.append(node)
            for dep in adj.get(node, []):
                if dep not in valid_ids:
                    continue
                if dep not in visited:
                    result = dfs(dep)
                    if result:
                        return result
                elif dep in stack:
                    cycle_start = path.index(dep)
                    return path[cycle_start:] + [dep]
            path.pop()
            stack.remove(node)
            return []

        for nid in sorted(valid_ids):
            if nid not in visited:
                found = dfs(nid)
                if found:
                    return found
        return []

    def _static_args_for_validation(self, raw_args: Dict[str, Any]) -> Dict[str, Any]:
        return {
            key: static_placeholder_for_validation(value)
            for key, value in raw_args.items()
        }

    def _extract_artifact_refs(self, value: Any) -> List[str]:
        refs: List[str] = []
        if isinstance(value, dict):
            if "$artifact" in value and isinstance(value["$artifact"], str):
                refs.append(value["$artifact"])
            if "$ref" in value and isinstance(value["$ref"], str):
                refs.append(value["$ref"])
            if "$sources" in value and isinstance(value["$sources"], list):
                for src in value["$sources"]:
                    refs.extend(self._extract_artifact_refs(src))
            for v in value.values():
                if v is not value.get("$sources"):
                    refs.extend(self._extract_artifact_refs(v))
        elif isinstance(value, list):
            for item in value:
                refs.extend(self._extract_artifact_refs(item))
        elif isinstance(value, str):
            import re
            m = re.match(r"^(n\d+)\.output$", value)
            if m:
                refs.append(m.group(1))
            m2 = re.match(r"^dependency\[(n\d+)\]$", value)
            if m2:
                refs.append(m2.group(1))
        return refs
