from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


# ====================================================
# ERROR TYPES
# ====================================================

class ErrorType:
    SUCCESS = "success"
    RETRYABLE_FAIL = "fail"
    FATAL_ERROR = "fatal_error"


class UnresolvedDependencyError(Exception):
    """Raised when an artifact reference cannot be resolved before tool execution."""

    def __init__(self, message: str = "Unresolved dependency"):
        super().__init__(message)
        self.message = message


# ====================================================
# CAPABILITY VIOLATION TYPES (v1.5)
# ====================================================

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


class CapabilityViolationError(Exception):
    """
    Raised when a capability violation is detected before or during execution.

    Carries structured violation data for deterministic failure reporting.
    """

    def __init__(
        self,
        violation_type: ViolationType,
        node_id: str,
        tool_name: str,
        description: str = "",
        capability_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.violation_type = violation_type
        self.node_id = node_id
        self.tool_name = tool_name
        self.capability_id = capability_id
        self.description = description
        self.details = details or {}
        super().__init__(description)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_type": self.violation_type.value,
            "node_id": self.node_id,
            "tool_name": self.tool_name,
            "capability_id": self.capability_id,
            "description": self.description,
            "details": dict(self.details),
        }


# ====================================================
# STANDARD RESULT FACTORIES
# ====================================================

def success(output=None, step=None):
    return {
        "status": ErrorType.SUCCESS,
        "output": output,
        "step": step
    }


def fail(reason: str, fix: str = None, step: dict = None):
    return {
        "status": ErrorType.RETRYABLE_FAIL,
        "error": reason,
        "fix": fix,
        "step": step
    }


def fatal(reason: str, step: dict = None):
    return {
        "status": ErrorType.FATAL_ERROR,
        "error": reason,
        "step": step
    }


# ====================================================
# STATUS HELPERS
# ====================================================

def is_success(result: dict) -> bool:
    return result.get("status") == ErrorType.SUCCESS


def is_fail(result: dict) -> bool:
    return result.get("status") == ErrorType.RETRYABLE_FAIL


def is_fatal(result: dict) -> bool:
    return result.get("status") == ErrorType.FATAL_ERROR
