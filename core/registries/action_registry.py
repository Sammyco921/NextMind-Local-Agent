# core/registries/action_registry.py
"""
Registry for action types used in planning.

Actions represent atomic operations that can be performed during execution.
Each action has capabilities that define what it can do and what it requires.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from core.registries.base import Registry


@dataclass(frozen=True)
class Capability:
    """
    A capability that an action provides or requires.
    
    Capabilities enable capability-based planning where actions are
    selected based on what they can do, not just their names.
    """
    capability_id: str
    description: str
    input_types: Set[str] = field(default_factory=set)  # Types it consumes
    output_types: Set[str] = field(default_factory=set)  # Types it produces
    side_effects: Set[str] = field(default_factory=set)  # Side effect types
    constraints: Set[str] = field(default_factory=set)  # Constraint types it enforces


@dataclass(frozen=True)
class ActionSpec:
    """
    Specification for an action type.
    
    Actions are the atomic units of planning. Each action corresponds
    to a tool operation that will become a DAG node.
    """
    action_type: str
    display_name: str
    description: str
    capabilities: List[Capability]
    required_capabilities: List[str] = field(default_factory=list)  # Capability IDs
    optional_capabilities: List[str] = field(default_factory=list)
    default_transform: Optional[str] = None  # Default transform if applicable
    version: str = "1.0.0"


class ActionRegistry(Registry[ActionSpec]):
    """
    Registry for action types.
    
    Actions are discovered by their capabilities, enabling flexible
    planning that adapts to available tools.
    """

    def __init__(self):
        self._actions: Dict[str, ActionSpec] = {}

    def register(
        self, spec: ActionSpec, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        if spec.action_type in self._actions:
            raise ValueError(f"Action already registered: {spec.action_type}")
        if not spec.capabilities:
            raise ValueError(f"Action must have at least one capability: {spec.action_type}")
        
        self._actions[spec.action_type] = spec

    def get(self, action_type: str) -> ActionSpec:
        if action_type not in self._actions:
            raise KeyError(f"Unknown action: {action_type}")
        return self._actions[action_type]

    def has(self, action_type: str) -> bool:
        return action_type in self._actions

    def keys(self) -> List[str]:
        return sorted(self._actions.keys())

    def validate(self, action_type: str, context: Dict[str, Any]) -> List[str]:
        if action_type not in self._actions:
            return [f"Unknown action: {action_type}"]

        spec = self._actions[action_type]
        errors: List[str] = []

        # Check required capabilities are available
        available_caps = context.get("available_capabilities", set())
        for req_cap in spec.required_capabilities:
            if req_cap not in available_caps:
                errors.append(f"Action requires capability: {req_cap}")

        return errors

    def get_metadata(self, key: str) -> Dict[str, Any]:
        action = self._actions.get(key)
        if action:
            return {
                "display_name": action.display_name,
                "description": action.description,
                "capabilities": [c.capability_id for c in action.capabilities],
            }
        return {}

    def find_by_capability(self, capability_id: str) -> List[str]:
        """
        Find all actions that provide a specific capability.
        
        Args:
            capability_id: The capability to search for
            
        Returns:
            Sorted list of action types that provide the capability
        """
        results: List[str] = []
        for action_type, spec in self._actions.items():
            for cap in spec.capabilities:
                if capability_id == cap.capability_id:
                    results.append(action_type)
                    break
        return sorted(results)

    def get_action_capabilities(self, action_type: str) -> List[Capability]:
        """
        Get all capabilities for an action.
        
        Args:
            action_type: The action type
            
        Returns:
            List of capabilities (empty if action not found)
        """
        if action_type not in self._actions:
            return []
        return list(self._actions[action_type].capabilities)