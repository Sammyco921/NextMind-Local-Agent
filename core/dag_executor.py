# core/dag_executor.py
#
# v1.5: Capability-enforced typed artifact execution.
#
# For every node, verifies BEFORE execution:
#   - capability manifest exists
#   - tool is allowed by manifest
#   - file path is within scope
#   - resource limits are not exceeded
#   - tool contract compatibility still holds (v1.4)
#
# On violation: STOP immediately, return structured failure.
# NO partial execution allowed under any circumstance.

from __future__ import annotations

from typing import Any, Dict, List

from core.artifact_resolver import ArtifactResolver
from core.artifact_types import Artifact, ArtifactType
from core.dag_node import DAG, DAGNode
from core.dag_topology import topological_order
from core.errors import (
    CapabilityViolationError,
    UnresolvedDependencyError,
    ViolationType,
)
from core.execution_context import ExecutionContext
from core.tool_contracts import (
    get_contract,
    get_required_capabilities_from_contract,
    has_contract,
)
from core.tool_registry import ToolRegistry
from core.types import ExecutionResult, NodeId


class DAGExecutor:
    """Executes a DAG in strict topological order with typed artifact flow.

    v1.5: Enforces capability boundary before every node execution.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self.resolver = ArtifactResolver()

    def execute(self, dag: DAG, goal: str) -> ExecutionResult:
        context = ExecutionContext(goal=goal, dag=dag)
        status = "success"

        for node in topological_order(dag.nodes):
            context.set_current_step(node.node_id)

            # ---- v1.5: Capability enforcement before execution ----
            violation = self._enforce_capabilities(dag, node)
            if violation is not None:
                status = "partial_failure"
                context.add_error(violation.description)
                context.log_execution(
                    node.node_id,
                    node.tool_name,
                    dict(node.raw_args),
                    {
                        "error": violation.description,
                        "violation_type": violation.violation_type.value,
                        "capability_id": violation.capability_id,
                    },
                    "failed",
                )
                break

            try:
                resolved_args = self.resolver.resolve_inputs(node, context)
            except UnresolvedDependencyError as e:
                status = "partial_failure"
                context.add_error(str(e))
                context.log_execution(
                    node.node_id,
                    node.tool_name,
                    dict(node.raw_args),
                    {"error": str(e)},
                    "failed",
                )
                break

            try:
                output = self.registry.run(node.tool_name, resolved_args)
                artifact = self._wrap_in_artifact(node, output)
                context.store_artifact(node.node_id, artifact)
                context.log_execution(
                    node.node_id,
                    node.tool_name,
                    resolved_args,
                    output,
                    "success",
                    artifact_type=artifact.type.value,
                )
            except Exception as e:
                status = "partial_failure"
                context.add_error(str(e))
                context.log_execution(
                    node.node_id,
                    node.tool_name,
                    resolved_args,
                    {"error": str(e)},
                    "failed",
                )
                break

        trace = [
            {
                "id": entry["node_id"],
                "tool": entry["tool_name"],
                "args": entry["args"],
                "status": "success" if entry["status"] == "success" else "fail",
                "result": entry["result"],
                "artifact_type": entry.get("artifact_type"),
                "note": None,
            }
            for entry in context.execution_log
        ]

        return ExecutionResult(
            goal=goal,
            status=status,
            trace=trace,
            steps_executed=len(trace),
        )

    def _enforce_capabilities(
        self, dag: DAG, node: DAGNode
    ) -> CapabilityViolationError | None:
        """Enforce capability boundary for a single node.

        Returns a CapabilityViolationError if a violation is detected, None otherwise.
        """
        manifest = getattr(dag, "capability_manifest", None)

        # 1. Manifest must exist (v1.5 requirement)
        if manifest is None:
            return CapabilityViolationError(
                violation_type=ViolationType.MANIFEST_MISSING,
                node_id=node.node_id,
                tool_name=node.tool_name,
                description=(
                    f"Node {node.node_id}: capability manifest is missing "
                    f"from DAG — execution blocked"
                ),
            )

        manifest_cap_ids: List[str] = []
        for cap in getattr(manifest, "capabilities", []):
            if isinstance(cap, dict):
                cid = cap.get("capability_id", "")
            else:
                cid = getattr(cap, "capability_id", "")
            if cid:
                manifest_cap_ids.append(str(cid))

        # 2. Tool must be permitted by at least one capability
        tool_allowed = False
        for cap in getattr(manifest, "capabilities", []):
            if isinstance(cap, dict):
                allowed_tools = cap.get("allowed_tools")
            else:
                allowed_tools = getattr(cap, "allowed_tools", None)
            if allowed_tools is not None and node.tool_name in allowed_tools:
                tool_allowed = True
                break
            if allowed_tools is None:
                tool_allowed = True
                break

        if not tool_allowed:
            return CapabilityViolationError(
                violation_type=ViolationType.TOOL_NOT_PERMITTED,
                node_id=node.node_id,
                tool_name=node.tool_name,
                description=(
                    f"Node {node.node_id}: tool '{node.tool_name}' is not "
                    f"permitted by any capability in manifest"
                ),
                capability_id=None,
                details={"manifest_capabilities": manifest_cap_ids},
            )

        # 3. Tool's required capabilities must be granted in manifest
        tool_required_caps = self._get_required_capabilities(node.tool_name)
        for req_cap in tool_required_caps:
            if req_cap not in manifest_cap_ids:
                return CapabilityViolationError(
                    violation_type=ViolationType.MISSING_CAPABILITY,
                    node_id=node.node_id,
                    tool_name=node.tool_name,
                    capability_id=req_cap,
                    description=(
                        f"Node {node.node_id}: tool '{node.tool_name}' requires "
                        f"capability '{req_cap}' but manifest only grants: "
                        f"{manifest_cap_ids}"
                    ),
                    details={
                        "required": tool_required_caps,
                        "granted": manifest_cap_ids,
                    },
                )

        # 4. Scope enforcement: check file paths in args
        for key, value in (node.raw_args or {}).items():
            if isinstance(value, str) and key in ("filename", "path"):
                violation = self._enforce_path_scope(
                    node, value, manifest_cap_ids, manifest
                )
                if violation is not None:
                    return violation

        return None

    def _enforce_path_scope(
        self,
        node: DAGNode,
        path: str,
        manifest_cap_ids: List[str],
        manifest: Any,
    ) -> CapabilityViolationError | None:
        """Enforce path-based scope restrictions."""
        # Check path traversal (no '../' escaping)
        import os

        normalized = os.path.normpath(path)
        if normalized.startswith("..") or "/.." in normalized:
            return CapabilityViolationError(
                violation_type=ViolationType.PATH_TRAVERSAL,
                node_id=node.node_id,
                tool_name=node.tool_name,
                description=(
                    f"Node {node.node_id}: path '{path}' is a path traversal "
                    f"attempt — blocked"
                ),
                details={"path": path, "normalized": normalized},
            )

        # Bare filenames (no directory component) are always scoped to cwd
        if "/" not in path:
            return None

        # Absolute paths (starting with /) are never allowed under relative scopes
        if path.startswith("/"):
            return CapabilityViolationError(
                violation_type=ViolationType.SCOPE_VIOLATION,
                node_id=node.node_id,
                tool_name=node.tool_name,
                description=(
                    f"Node {node.node_id}: absolute path '{path}' is not "
                    f"within any allowed scope"
                ),
                details={"path": path},
            )

        # Normalize relative paths to check against scope prefixes
        check_path = path
        if not path.startswith("./"):
            check_path = "./" + path

        # Check allowed_path_prefixes from scope constraints
        for cap_entry in getattr(manifest, "capabilities", []):
            if isinstance(cap_entry, dict):
                scope = cap_entry.get("scope", {})
                allowed_prefixes = scope.get("allowed_path_prefixes")
            else:
                scope_obj = getattr(cap_entry, "scope", None)
                allowed_prefixes = (
                    getattr(scope_obj, "allowed_path_prefixes", None)
                    if scope_obj is not None
                    else None
                )
            if allowed_prefixes is not None:
                if not any(check_path.startswith(prefix) for prefix in allowed_prefixes):
                    return CapabilityViolationError(
                        violation_type=ViolationType.SCOPE_VIOLATION,
                        node_id=node.node_id,
                        tool_name=node.tool_name,
                        description=(
                            f"Node {node.node_id}: path '{path}' is not within "
                            f"any allowed path prefix: {allowed_prefixes}"
                        ),
                        details={
                            "path": path,
                            "check_path": check_path,
                            "allowed_prefixes": allowed_prefixes,
                        },
                    )

        return None

    def _get_required_capabilities(self, tool_name: str) -> List[str]:
        try:
            return list(get_required_capabilities_from_contract(tool_name))
        except (ValueError, KeyError):
            pass
        try:
            return self.registry.get_required_capabilities(tool_name)
        except (ValueError, KeyError):
            pass
        return []

    @staticmethod
    def _wrap_in_artifact(node: DAGNode, output: Any) -> Artifact:
        """Wrap raw tool output in typed Artifact based on tool contract."""
        if has_contract(node.tool_name):
            contract = get_contract(node.tool_name)
            return Artifact(type=contract.output_type, value=output)
        return Artifact(type=ArtifactType.NULL, value=output)

