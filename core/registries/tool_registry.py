# core/registries/tool_registry.py
"""
Registry for tools with capability-based discovery.

Tools are the actual implementations that execute during the execution phase.
Each tool exposes capabilities that describe what it can do.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from core.registries.base import Registry


class SafetyLevel(Enum):
    """Safety classification for tools."""
    SAFE = "safe"  # No side effects, read-only
    CAUTIOUS = "cautious"  # May modify state, reversible
    RISKY = "risky"  # May modify state, irreversible
    DANGEROUS = "dangerous"  # System-level operations


class EffectType(Enum):
    """Types of effects a tool can have."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MODIFY = "modify"
    CREATE = "create"
    EXECUTE = "execute"
    QUERY = "query"


@dataclass(frozen=True)
class ToolEffect:
    """
    Description of a tool's effect on the world.
    
    Effects are used for safety analysis and constraint checking.
    """
    effect_type: EffectType
    resource_type: str  # "file", "directory", "process", "network", etc.
    description: str
    reversible: bool = False
    constraints: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ToolCapability:
    """
    A capability provided by a tool.
    
    Capabilities define what a tool can do, what inputs it needs,
    and what outputs it produces.
    """
    capability_id: str
    description: str
    input_schema: Dict[str, Any]  # JSON Schema for inputs
    output_schema: Dict[str, Any]  # JSON Schema for outputs
    effects: List[ToolEffect] = field(default_factory=list)
    produces_types: Set[str] = field(default_factory=set)  # Output types
    consumes_types: Set[str] = field(default_factory=set)  # Input types


@dataclass(frozen=True)
class ToolSpec:
    """
    Complete specification for a tool.
    
    Tools are the actual implementations that execute during runtime.
    """
    tool_id: str
    display_name: str
    description: str
    executor: Callable[..., Any]  # The actual tool function
    capabilities: List[ToolCapability]
    safety_level: SafetyLevel = SafetyLevel.SAFE
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    timeout_ms: Optional[int] = None  # Execution timeout
    version: str = "1.0.0"


class ToolCapabilityRegistry(Registry[ToolSpec]):
    """
    Registry for tools with capability-based discovery.
    
    Tools are discovered by their capabilities, enabling flexible
    execution that adapts to available tools.
    """

    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}

    def register(
        self, spec: ToolSpec, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        if spec.tool_id in self._tools:
            raise ValueError(f"Tool already registered: {spec.tool_id}")
        if not spec.capabilities:
            raise ValueError(f"Tool must have at least one capability: {spec.tool_id}")
        
        self._tools[spec.tool_id] = spec

    def get(self, tool_id: str) -> ToolSpec:
        if tool_id not in self._tools:
            raise KeyError(f"Unknown tool: {tool_id}")
        return self._tools[tool_id]

    def has(self, tool_id: str) -> bool:
        return tool_id in self._tools

    def keys(self) -> List[str]:
        return sorted(self._tools.keys())

    def validate(self, tool_id: str, context: Dict[str, Any]) -> List[str]:
        if tool_id not in self._tools:
            return [f"Unknown tool: {tool_id}"]

        spec = self._tools[tool_id]
        errors: List[str] = []

        # Check resource requirements
        for resource in spec.resource_requirements:
            if resource not in context.get("available_resources", {}):
                errors.append(f"Tool requires resource: {resource}")

        return errors

    def get_metadata(self, key: str) -> Dict[str, Any]:
        tool = self._tools.get(key)
        if tool:
            return {
                "display_name": tool.display_name,
                "description": tool.description,
                "safety_level": tool.safety_level.value,
                "capabilities": [c.capability_id for c in tool.capabilities],
            }
        return {}

    def find_by_capability(self, capability_id: str) -> List[str]:
        """
        Find all tools that provide a specific capability.
        
        Args:
            capability_id: The capability to search for
            
        Returns:
            Sorted list of tool IDs that provide the capability
        """
        results: List[str] = []
        for tool_id, spec in self._tools.items():
            for cap in spec.capabilities:
                if cap.capability_id == capability_id:
                    results.append(tool_id)
                    break
        return sorted(results)

    def find_by_safety(self, max_safety: SafetyLevel) -> List[str]:
        """
        Find all tools at or below a safety level.
        
        Args:
            max_safety: Maximum allowed safety level
            
        Returns:
            Sorted list of tool IDs at or below the safety level
        """
        safety_order = [SafetyLevel.SAFE, SafetyLevel.CAUTIOUS, SafetyLevel.RISKY, SafetyLevel.DANGEROUS]
        max_index = safety_order.index(max_safety)
        results: List[str] = []
        for tool_id, spec in self._tools.items():
            if safety_order.index(spec.safety_level) <= max_index:
                results.append(tool_id)
        return sorted(results)

    def execute(self, tool_id: str, args: Dict[str, Any]) -> Any:
        """
        Execute a tool with validated arguments.
        
        Args:
            tool_id: The tool to execute
            args: Arguments to pass to the tool
            
        Returns:
            The tool's output
            
        Raises:
            ValueError: If arguments don't match the schema
            KeyError: If tool is not found
        """
        spec = self.get(tool_id)

        # Basic validation - check required fields in all capability schemas
        for cap in spec.capabilities:
            for field_name, schema in cap.input_schema.items():
                if isinstance(schema, dict) and schema.get("required", False):
                    if field_name not in args:
                        raise ValueError(f"Missing required argument: {field_name}")

        return spec.executor(**args)

    def get_tool_capabilities(self, tool_id: str) -> List[ToolCapability]:
        """
        Get all capabilities for a tool.
        
        Args:
            tool_id: The tool ID
            
        Returns:
            List of capabilities (empty if tool not found)
        """
        if tool_id not in self._tools:
            return []
        return list(self._tools[tool_id].capabilities)