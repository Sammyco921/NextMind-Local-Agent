# core/contracts.py
"""
NextMind v1.2 Execution Contract Layer

Enforces structural and capability contracts before execution.
No execution is allowed without passing contract validation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import re


class ContractViolationType(Enum):
    """Types of contract violations."""
    MISSING_CAPABILITY = "missing_capability"
    INVALID_ARGUMENT = "invalid_argument"
    MISSING_DEPENDENCY = "missing_dependency"
    CYCLE_DETECTED = "cycle_detected"
    ORPHAN_NODE = "orphan_node"
    UNREACHABLE_NODE = "unreachable_node"
    INVALID_TRANSFORM = "invalid_transform"
    MISSING_ARTIFACT = "missing_artifact"
    SCHEMA_MISMATCH = "schema_mismatch"
    RESOURCE_UNAVAILABLE = "resource_unavailable"


class ContractSeverity(Enum):
    """Severity of contract violations."""
    FATAL = "fatal"      # Blocks all execution
    ERROR = "error"      # Must be resolved
    WARNING = "warning"  # Non-blocking


@dataclass(frozen=True)
class ContractViolation:
    """A single contract violation."""
    violation_type: ContractViolationType
    severity: ContractSeverity
    node_id: Optional[str] = None
    action_type: Optional[str] = None
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_type": self.violation_type.value,
            "severity": self.severity.value,
            "node_id": self.node_id,
            "action_type": self.action_type,
            "description": self.description,
            "details": self.details,
        }


@dataclass
class ContractResult:
    """Result of contract validation."""
    passed: bool
    violations: List[ContractViolation] = field(default_factory=list)
    warnings: List[ContractViolation] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(v.severity == ContractSeverity.ERROR for v in self.violations)

    @property
    def has_fatal(self) -> bool:
        return any(v.severity == ContractSeverity.FATAL for v in self.violations)

    @property
    def is_blocking(self) -> bool:
        return self.has_errors or self.has_fatal

    def add_violation(self, violation: ContractViolation) -> None:
        if violation.severity == ContractSeverity.WARNING:
            self.warnings.append(violation)
        else:
            self.violations.append(violation)

    def merge(self, other: "ContractResult") -> None:
        """Merge another contract result into this one."""
        self.violations.extend(other.violations)
        self.warnings.extend(other.warnings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed and not self.is_blocking,
            "violations": [v.to_dict() for v in self.violations],
            "warnings": [v.to_dict() for v in self.warnings],
            "has_errors": self.has_errors,
            "has_fatal": self.has_fatal,
            "is_blocking": self.is_blocking,
        }


class ExecutionContractLayer:
    """
    Validates execution contracts before any execution is allowed.
    
    This is the gatekeeper between planning and execution. No DAG
    may be executed without passing contract validation.
    """

    def __init__(
        self,
        action_registry: Optional[Any] = None,
        tool_registry: Optional[Any] = None,
        transform_registry: Optional[Any] = None,
    ):
        self.action_registry = action_registry
        self.tool_registry = tool_registry
        self.transform_registry = transform_registry

    def validate_action_spec(
        self,
        action_type: str,
        entities: Dict[str, Any],
        available_capabilities: Optional[Set[str]] = None,
    ) -> ContractResult:
        """
        Validate an ActionSpec against allowed capabilities.
        
        Args:
            action_type: The action type to validate
            entities: The entities/arguments for the action
            available_capabilities: Set of available capability IDs
            
        Returns:
            ContractResult with any violations
        """
        result = ContractResult(passed=True)

        if not self.action_registry:
            return result

        # Check action exists
        if not self.action_registry.has(action_type):
            result.add_violation(ContractViolation(
                violation_type=ContractViolationType.MISSING_CAPABILITY,
                severity=ContractSeverity.ERROR,
                action_type=action_type,
                description=f"Unknown action type: {action_type}",
            ))
            return result

        action_spec = self.action_registry.get(action_type)

        # Check required capabilities (use 'is not None' to handle empty sets)
        if available_capabilities is not None:
            for req_cap in action_spec.required_capabilities:
                if req_cap not in available_capabilities:
                    result.add_violation(ContractViolation(
                        violation_type=ContractViolationType.MISSING_CAPABILITY,
                        severity=ContractSeverity.ERROR,
                        action_type=action_type,
                        description=f"Action '{action_type}' requires capability: {req_cap}",
                        details={"required_capability": req_cap},
                    ))

        # Validate entities against tool schema
        if self.tool_registry and self.tool_registry.has(action_type):
            tool_spec = self.tool_registry.get(action_type)
            for cap in tool_spec.capabilities:
                for field_name, schema in cap.input_schema.items():
                    if isinstance(schema, dict) and schema.get("required", False):
                        if field_name not in entities:
                            result.add_violation(ContractViolation(
                                violation_type=ContractViolationType.INVALID_ARGUMENT,
                                severity=ContractSeverity.ERROR,
                                action_type=action_type,
                                node_id=None,
                                description=f"Missing required argument: {field_name}",
                                details={"field": field_name},
                            ))

        return result

    def validate_dag_structure(
        self,
        nodes: List[Any],
        artifacts: Optional[Dict[str, Any]] = None,
    ) -> ContractResult:
        """
        Validate DAG structural constraints before execution.
        
        Args:
            nodes: List of DAGNode objects
            artifacts: Optional artifact mapping
            
        Returns:
            ContractResult with any violations
        """
        result = ContractResult(passed=True)

        if not nodes:
            result.add_violation(ContractViolation(
                violation_type=ContractViolationType.ORPHAN_NODE,
                severity=ContractSeverity.ERROR,
                description="DAG has no nodes",
            ))
            return result

        node_ids: Set[str] = {n.node_id for n in nodes}
        all_dependencies: Set[str] = set()

        for node in nodes:
            # Collect all dependencies
            if hasattr(node, "dependencies"):
                all_dependencies.update(node.dependencies)

            # Check for orphan nodes (dependencies on non-existent nodes)
            for dep in getattr(node, "dependencies", []):
                if dep not in node_ids:
                    result.add_violation(ContractViolation(
                        violation_type=ContractViolationType.MISSING_DEPENDENCY,
                        severity=ContractSeverity.ERROR,
                        node_id=node.node_id,
                        description=f"Node '{node.node_id}' depends on non-existent node: {dep}",
                        details={"missing_dependency": dep},
                    ))

        # Check for unreachable nodes (nodes not reachable from roots)
        root_ids = {n.node_id for n in nodes if not getattr(n, "dependencies", set())}
        reachable = self._compute_reachable(nodes, root_ids)
        
        for node in nodes:
            if node.node_id not in reachable:
                result.add_violation(ContractViolation(
                    violation_type=ContractViolationType.UNREACHABLE_NODE,
                    severity=ContractSeverity.WARNING,
                    node_id=node.node_id,
                    description=f"Node '{node.node_id}' is not reachable from any root",
                ))

        # Check for cycles
        cycles = self._detect_cycles(nodes)
        if cycles:
            result.add_violation(ContractViolation(
                violation_type=ContractViolationType.CYCLE_DETECTED,
                severity=ContractSeverity.FATAL,
                description=f"Cycles detected in DAG: {cycles}",
                details={"cycles": cycles},
            ))

        # Validate artifact references
        if artifacts:
            for node in nodes:
                raw_args = getattr(node, "raw_args", {})
                for key, value in raw_args.items():
                    if isinstance(value, str) and value.startswith("$"):
                        # Check artifact reference exists
                        ref = value.lstrip("$")
                        if ref not in artifacts and ref not in node_ids:
                            result.add_violation(ContractViolation(
                                violation_type=ContractViolationType.MISSING_ARTIFACT,
                                severity=ContractSeverity.ERROR,
                                node_id=node.node_id,
                                description=f"Node '{node.node_id}' references unknown artifact: {ref}",
                                details={"reference": ref},
                            ))

        # Update passed status
        result.passed = not result.is_blocking
        return result

    def validate_transform(
        self,
        transform_id: str,
        inputs: Dict[str, Any],
    ) -> ContractResult:
        """
        Validate a transform before execution.
        
        Args:
            transform_id: The transform to validate
            inputs: Input values for the transform
            
        Returns:
            ContractResult with any violations
        """
        result = ContractResult(passed=True)

        if not self.transform_registry:
            return result

        if not self.transform_registry.has(transform_id):
            result.add_violation(ContractViolation(
                violation_type=ContractViolationType.INVALID_TRANSFORM,
                severity=ContractSeverity.ERROR,
                description=f"Unknown transform: {transform_id}",
                details={"transform_id": transform_id},
            ))
            return result

        spec = self.transform_registry.get(transform_id)
        
        # Validate required inputs
        for input_spec in spec.input_schema:
            if input_spec.required and input_spec.field_name not in inputs:
                result.add_violation(ContractViolation(
                    violation_type=ContractViolationType.INVALID_ARGUMENT,
                    severity=ContractSeverity.ERROR,
                    description=f"Transform '{transform_id}' missing required input: {input_spec.field_name}",
                    details={"field": input_spec.field_name},
                ))

        # Run spec-specific validator
        if spec.validator:
            errors = spec.validator(inputs)
            for error in errors:
                result.add_violation(ContractViolation(
                    violation_type=ContractViolationType.SCHEMA_MISMATCH,
                    severity=ContractSeverity.ERROR,
                    description=error,
                ))

        result.passed = not result.is_blocking
        return result

    def validate_full_plan(
        self,
        nodes: List[Any],
        actions: Optional[List[Any]] = None,
        artifacts: Optional[Dict[str, Any]] = None,
    ) -> ContractResult:
        """
        Full contract validation for an execution plan.
        
        Combines all validation checks into a single result.
        
        Args:
            nodes: List of DAGNode objects
            actions: Optional list of ActionSpec objects
            artifacts: Optional artifact mapping
            
        Returns:
            ContractResult with all violations
        """
        result = ContractResult(passed=True)

        # Validate DAG structure
        dag_result = self.validate_dag_structure(nodes, artifacts)
        result.merge(dag_result)

        # Validate each action
        if actions:
            available_caps = self._get_available_capabilities(nodes)
            for action in actions:
                action_type = getattr(action, "action_type", None)
                entities = {k: v.value for k, v in getattr(action, "entities", {}).items()}
                action_result = self.validate_action_spec(action_type, entities, available_caps)
                result.merge(action_result)

        # Validate transforms
        if self.transform_registry:
            for node in nodes:
                raw_args = getattr(node, "raw_args", {})
                transform = raw_args.get("$transform")
                if transform:
                    inputs = {k: v for k, v in raw_args.items() if k != "$transform"}
                    transform_result = self.validate_transform(transform, inputs)
                    result.merge(transform_result)

        result.passed = not result.is_blocking
        return result

    def _compute_reachable(
        self,
        nodes: List[Any],
        root_ids: Set[str],
    ) -> Set[str]:
        """Compute set of node IDs reachable from roots."""
        reachable: Set[str] = set()
        queue = list(root_ids)
        
        # Build adjacency map
        children: Dict[str, List[str]] = {n.node_id: [] for n in nodes}
        for node in nodes:
            for dep in getattr(node, "dependencies", []):
                if dep in children:
                    children[dep].append(node.node_id)
        
        while queue:
            node_id = queue.pop(0)
            if node_id in reachable:
                continue
            reachable.add(node_id)
            queue.extend(children.get(node_id, []))
        
        return reachable

    def _detect_cycles(self, nodes: List[Any]) -> List[List[str]]:
        """Detect cycles in the DAG using DFS."""
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        in_stack: Set[str] = set()
        stack: List[str] = []
        
        # Build adjacency map
        edges: Dict[str, List[str]] = {}
        for node in nodes:
            node_id = node.node_id
            edges[node_id] = list(getattr(node, "dependencies", []))
        
        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            in_stack.add(node_id)
            stack.append(node_id)
            
            for dep in sorted(edges.get(node_id, [])):
                if dep not in visited:
                    if dep in edges and dfs(dep):
                        return True
                elif dep in in_stack:
                    # Found cycle
                    cycle_start = stack.index(dep)
                    cycle = stack[cycle_start:] + [dep]
                    cycles.append(cycle)
                    return True
            
            stack.pop()
            in_stack.remove(node_id)
            return False
        
        for node in sorted(nodes, key=lambda n: n.node_id):
            if node.node_id not in visited:
                dfs(node.node_id)
        
        return cycles

    def _get_available_capabilities(self, nodes: List[Any]) -> Set[str]:
        """Get set of capabilities available from nodes."""
        capabilities: Set[str] = set()
        
        if not self.tool_registry:
            return capabilities
        
        for node in nodes:
            raw_args = getattr(node, "raw_args", {})
            tool_id = raw_args.get("tool") or raw_args.get("$tool")
            if tool_id and self.tool_registry.has(tool_id):
                tool_spec = self.tool_registry.get(tool_id)
                for cap in tool_spec.capabilities:
                    capabilities.add(cap.capability_id)
        
        return capabilities


# ====================================================
# LEGACY CONTRACT SCHEMAS (for backward compatibility)
# ====================================================

EXECUTOR_RESPONSE_SCHEMA = {
    "status": str,
    "output": (dict, type(None)),
    "error": (str, type(None)),
    "step": dict,
}

TOOL_STEP_SCHEMA = {
    "id": str,
    "tool": str,
    "args": dict,
}

PLANNER_OUTPUT_SCHEMA = {
    "steps": list,
}

GOAL_MODEL_SCHEMA = {
    "intent": str,
    "entities": dict,
    "raw": str,
}

TOOL_REGISTRY_SCHEMA = {
    "name": str,
    "func": object,
    "description": str,
    "schema": dict,
}


def validate_contract(
    obj: Dict[str, Any],
    schema: Dict[str, Any],
    name: str = "Contract"
) -> None:
    """
    Lightweight deterministic schema validator.
    Legacy function for backward compatibility.
    """
    if not isinstance(obj, dict):
        raise TypeError(f"{name}: object must be dict")

    for key in schema:
        if key not in obj:
            raise ValueError(f"{name}: missing key '{key}'")

    for key, expected_type in schema.items():
        value = obj[key]
        if not isinstance(value, expected_type):
            if isinstance(expected_type, tuple):
                valid = any(isinstance(value, t) for t in expected_type)
                if not valid:
                    raise TypeError(
                        f"{name}: key '{key}' invalid type "
                        f"(expected {expected_type}, got {type(value)})"
                    )
            else:
                raise TypeError(
                    f"{name}: key '{key}' expected "
                    f"{expected_type.__name__}, got "
                    f"{type(value).__name__}"
                )
