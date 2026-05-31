# core/type_validator.py
#
# v1.4 type flow validation — enforces artifact type compatibility between DAG nodes.
#
# Pure function: (DAG, contract_lookup) → errors[]
# No state, no history, no semantic bias.

from __future__ import annotations

from typing import Any, Callable, Dict, List

from core.artifact_types import ArtifactType
from core.dag_node import DAG, DAGNode


def validate_type_flow(
    dag: DAG,
    contract_lookup: Callable[[str], Any],
) -> List[str]:
    """
    Validate typed artifact flows in a DAG.

    Checks:
    - Every node's tool has a declared contract
    - Each dependency node's declared output type matches what the consuming arg expects
    - No self-inconsistent artifact_type declarations
    """
    errors: List[str] = []
    nodes = dag.nodes

    if not nodes:
        return errors

    node_map: Dict[str, DAGNode] = {n.node_id: n for n in nodes}

    for node in nodes:
        try:
            contract = contract_lookup(node.tool_name)
        except (ValueError, KeyError):
            errors.append(
                f"Node {node.node_id}: tool '{node.tool_name}' has no declared contract"
            )
            continue

        # Verify declared artifact_type in metadata matches contract
        declared_in_meta = node.metadata.get("artifact_type")
        if declared_in_meta is not None:
            try:
                meta_type = ArtifactType(declared_in_meta)
                if meta_type != contract.output_type:
                    errors.append(
                        f"Node {node.node_id}: metadata artifact_type "
                        f"'{declared_in_meta}' conflicts with contract "
                        f"output '{contract.output_type.value}'"
                    )
            except ValueError:
                errors.append(
                    f"Node {node.node_id}: invalid artifact_type "
                    f"in metadata: '{declared_in_meta}'"
                )

        # For each dependency, check the relevant arg's expected type
        for dep_id in node.dependencies:
            if dep_id not in node_map:
                continue

            # Find the consuming arg for this dependency
            consuming_arg = _find_consuming_arg(node, dep_id)
            if consuming_arg is None:
                continue

            expected_type = contract.input_types.get(consuming_arg)
            if expected_type is None:
                continue

            # Get the dependency node's output type from its contract
            dep_node = node_map[dep_id]
            try:
                dep_contract = contract_lookup(dep_node.tool_name)
            except (ValueError, KeyError):
                continue

            dep_output = dep_contract.output_type

            # Check for explicit override in metadata
            dep_declared = dep_node.metadata.get("artifact_type")
            if dep_declared is not None:
                try:
                    dep_output = ArtifactType(dep_declared)
                except ValueError:
                    pass

            if expected_type != dep_output:
                errors.append(
                    f"Node {node.node_id}: arg '{consuming_arg}' expects "
                    f"'{expected_type.value}' from '{dep_id}' but '{dep_id}' "
                    f"produces '{dep_output.value}' — explicit transform required"
                )

    return errors


def _find_consuming_arg(node: DAGNode, dep_id: str) -> str | None:
    """Find which arg in node consumes the output of dep_id."""
    args = node.raw_args or {}
    for key, value in args.items():
        if isinstance(value, dict):
            if value.get("$artifact") == dep_id:
                if "$field" in value:
                    return None  # field extraction changes type
                return key
        if isinstance(value, str):
            ref_match = f"$node:{dep_id}"
            if value == dep_id or value == ref_match:
                return key
    return None
