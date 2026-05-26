# core/capability.py
#
# v1.5 Capability-Based Execution Security Layer.
#
# Defines explicit execution permissions so that every DAG is executed
# only within a declared, immutable capability boundary.
#
# PRINCIPLE: If it is not explicitly permitted, it is forbidden.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ============================================================
# CAPABILITY IDENTIFIERS
# ============================================================

class CapabilityID(str, Enum):
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    FILESYSTEM_LIST = "filesystem.list"
    TOOL_EXECUTION = "tool.execution"

    def __str__(self) -> str:
        return self.value


# ============================================================
# CAPABILITY SCOPE
# ============================================================

@dataclass(frozen=True)
class CapabilityScope:
    """
    Restrictions for a capability — defines WHERE and HOW a capability can be used.

    All fields are optional. An empty/None field means no restriction.
    """

    allowed_paths: Optional[List[str]] = None
    allowed_path_prefixes: Optional[List[str]] = None
    max_bytes: Optional[int] = None
    max_outputs: Optional[int] = None
    max_steps: Optional[int] = None

    def allows_path(self, path: str) -> bool:
        if self.allowed_paths is not None and path not in self.allowed_paths:
            return False
        if self.allowed_path_prefixes is not None:
            if not any(path.startswith(prefix) for prefix in self.allowed_path_prefixes):
                return False
        return True

    def allows_byte_size(self, size: int) -> bool:
        if self.max_bytes is not None and size > self.max_bytes:
            return False
        return True

    def allows_step_count(self, count: int) -> bool:
        if self.max_steps is not None and count > self.max_steps:
            return False
        return True


# ============================================================
# CAPABILITY — single permission object
# ============================================================

@dataclass(frozen=True)
class Capability:
    """
    An explicit permission object.

    Each capability declares what it permits and under what constraints.
    """

    capability_id: CapabilityID
    display_name: str = ""
    description: str = ""
    scope: CapabilityScope = field(default_factory=CapabilityScope)
    allowed_tools: Optional[List[str]] = None
    constraints: Dict[str, Any] = field(default_factory=dict)

    def allows_tool(self, tool_name: str) -> bool:
        if self.allowed_tools is not None and tool_name not in self.allowed_tools:
            return False
        return True


# ============================================================
# CAPABILITY MANIFEST — attached to DAG, immutable
# ============================================================

@dataclass(frozen=True)
class CapabilityManifest:
    """
    Immutable capability declaration attached at DAG construction time.

    Missing manifest = execution failure.
    """

    dag_id: str
    capabilities: List[Capability] = field(default_factory=list)
    strict_mode: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_capability(self, cap_id: CapabilityID) -> bool:
        return any(c.capability_id == cap_id for c in self.capabilities)

    def get_capability(self, cap_id: CapabilityID) -> Optional[Capability]:
        for c in self.capabilities:
            if c.capability_id == cap_id:
                return c
        return None

    def allows_tool(self, tool_name: str) -> bool:
        for cap in self.capabilities:
            if cap.allows_tool(tool_name):
                return True
        return False

    def allows_path(self, path: str) -> bool:
        for cap in self.capabilities:
            if not cap.scope.allows_path(path):
                return False
        return True


# ============================================================
# CAPABILITY VIOLATION — structured failure result
# ============================================================

class ViolationType(Enum):
    MISSING_CAPABILITY = "missing_capability"
    SCOPE_VIOLATION = "scope_violation"
    TOOL_NOT_PERMITTED = "tool_not_permitted"
    RESOURCE_EXCEEDED = "resource_exceeded"
    MANIFEST_MISSING = "manifest_missing"
    MALFORMED_MANIFEST = "malformed_manifest"
    CAPABILITY_ESCALATION = "capability_escalation"
    TOOL_SPOOFING = "tool_spoofing"
    PATH_TRAVERSAL = "path_traversal"


@dataclass(frozen=True)
class CapabilityViolation:
    """
    Structured failure object for capability enforcement.

    Each violation is traceable to a specific node and capability.
    """

    violation_type: ViolationType
    node_id: str
    tool_name: str
    capability_id: Optional[str] = None
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_type": self.violation_type.value,
            "node_id": self.node_id,
            "tool_name": self.tool_name,
            "capability_id": self.capability_id,
            "description": self.description,
            "details": dict(self.details),
        }


# ============================================================
# CAPABILITY VIOLATION ERROR
# ============================================================

class CapabilityViolationError(Exception):
    """
    Raised when a capability violation is detected during execution.

    Carries a structured violation object for deterministic failure reporting.
    """

    def __init__(self, violation: CapabilityViolation) -> None:
        self.violation = violation
        super().__init__(violation.description)


# ============================================================
# CAPABILITY DERIVATION — deterministic, no heuristics
# ============================================================

# v1.5 canonical tool-to-capability mapping.
# Derived ONLY from tool contracts (v1.4) and explicit rule mapping.
# No heuristics, no model inference, no adaptive behavior.
_TOOL_REQUIRED_CAPABILITIES: Dict[str, List[CapabilityID]] = {
    "write_file": [CapabilityID.FILESYSTEM_WRITE, CapabilityID.TOOL_EXECUTION],
    "read_file": [CapabilityID.FILESYSTEM_READ, CapabilityID.TOOL_EXECUTION],
    "list_dir": [CapabilityID.FILESYSTEM_LIST, CapabilityID.TOOL_EXECUTION],
    "text_to_json": [CapabilityID.TOOL_EXECUTION],
    "json_to_text": [CapabilityID.TOOL_EXECUTION],
    "file_to_text": [CapabilityID.FILESYSTEM_READ, CapabilityID.TOOL_EXECUTION],
}


def get_required_capabilities(tool_name: str) -> List[CapabilityID]:
    """
    Get the list of CapabilityIDs required by a tool.

    Returns empty list for unknown tools (they will fail validation elsewhere).
    """
    return list(_TOOL_REQUIRED_CAPABILITIES.get(tool_name, []))


def known_capability_tools() -> Set[str]:
    return set(_TOOL_REQUIRED_CAPABILITIES.keys())


# ============================================================
# DEFAULT CAPABILITY MANIFEST BUILDER (deterministic)
# ============================================================

def build_default_manifest(dag_id: str, tool_names: Set[str]) -> CapabilityManifest:
    """
    Build a deterministic CapabilityManifest from a set of tool names.

    Derives capabilities ONLY from:
      - tool contracts (v1.4)
      - explicit rule mapping in _TOOL_REQUIRED_CAPABILITIES
    NOT from heuristics or model inference.
    """
    required_cap_ids: Set[CapabilityID] = set()
    for tool_name in tool_names:
        required_cap_ids.update(get_required_capabilities(tool_name))

    capabilities: List[Capability] = []
    for cap_id in sorted(required_cap_ids, key=str):
        caps = _build_capability_for_id(cap_id, tool_names)
        capabilities.extend(caps)

    return CapabilityManifest(
        dag_id=dag_id,
        capabilities=capabilities,
        strict_mode=True,
    )


def _build_capability_for_id(
    cap_id: CapabilityID,
    tool_names: Set[str],
) -> List[Capability]:
    """
    Build Capability objects for a given CapabilityID.

    All scopes are derived deterministically from tool contracts.
    """
    allowed_tools: List[str] = []
    for tool_name in sorted(tool_names):
        if cap_id in get_required_capabilities(tool_name):
            allowed_tools.append(tool_name)

    if cap_id == CapabilityID.FILESYSTEM_READ:
        return [
            Capability(
                capability_id=CapabilityID.FILESYSTEM_READ,
                display_name="Filesystem Read",
                description="Read files from the filesystem",
                allowed_tools=allowed_tools,
                scope=CapabilityScope(allowed_path_prefixes=["./"]),
            )
        ]
    elif cap_id == CapabilityID.FILESYSTEM_WRITE:
        return [
            Capability(
                capability_id=CapabilityID.FILESYSTEM_WRITE,
                display_name="Filesystem Write",
                description="Write files to the filesystem",
                allowed_tools=allowed_tools,
                scope=CapabilityScope(allowed_path_prefixes=["./"]),
            )
        ]
    elif cap_id == CapabilityID.FILESYSTEM_LIST:
        return [
            Capability(
                capability_id=CapabilityID.FILESYSTEM_LIST,
                display_name="Filesystem List",
                description="List directory contents",
                allowed_tools=allowed_tools,
                scope=CapabilityScope(allowed_path_prefixes=["./"]),
            )
        ]
    elif cap_id == CapabilityID.TOOL_EXECUTION:
        return [
            Capability(
                capability_id=CapabilityID.TOOL_EXECUTION,
                display_name="Tool Execution",
                description="Execute tools",
                allowed_tools=allowed_tools,
            )
        ]

    return []
