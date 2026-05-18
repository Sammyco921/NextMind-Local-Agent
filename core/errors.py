from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any, Dict


# ====================================================
# ERROR TYPES (STRICT, SINGLE SOURCE OF TRUTH)
# ====================================================

class ErrorType(str, Enum):
    SUCCESS = "success"
    FAIL = "fail"


# ====================================================
# CORE ERROR OBJECT (OPTIONAL STRUCTURED LAYER)
# ====================================================

@dataclass
class AgentError:
    status: str
    reason: str
    fix: Optional[str] = None
    step: Optional[Dict[str, Any]] = None
    output: Any = None


# ====================================================
# RESPONSE FACTORIES (THE ONLY THINGS YOU SHOULD USE)
# ====================================================

def success(output=None, step=None):
    """
    Canonical success response.
    """
    return {
        "status": ErrorType.SUCCESS,
        "output": output,
        "step": step
    }


def fail(reason: str, fix: str = None, step: dict = None):
    """
    Canonical failure response (retryable or recoverable).
    """
    return {
        "status": ErrorType.FAIL,
        "error": reason,
        "fix": fix,
        "step": step
    }


def fatal(reason: str, step: dict = None):
    """
    Fatal errors should still conform to system contract,
    but signal unrecoverable execution issues.
    """
    return {
        "status": ErrorType.FAIL,
        "error": reason,
        "step": step,
        "fatal": True
    }


# ====================================================
# STATUS CHECKERS (USED BY ORCHESTRATOR ONLY)
# ====================================================

def is_success(result: dict) -> bool:
    return result.get("status") == ErrorType.SUCCESS


def is_fail(result: dict) -> bool:
    return result.get("status") == ErrorType.FAIL


# ====================================================
# NORMALIZATION (VERY IMPORTANT FOR STABILITY)
# ====================================================

def normalize(result: dict) -> dict:
    """
    Ensures ALL components speak the same contract language.
    This prevents silent schema drift bugs.
    """

    if not isinstance(result, dict):
        return fail("Non-dict result returned by component")

    # Ensure status exists
    if "status" not in result:
        return fail("Missing status field in result")

    status = result["status"]

    if status not in ("success", "fail"):
        return fail(f"Invalid status value: {status}")

    # Ensure required fields exist for success
    if status == "success" and "output" not in result:
        return fail("Success result missing output field")

    # Ensure error field consistency
    if status == "fail" and "error" not in result:
        result["error"] = "Unknown failure"

    return result


# ====================================================
# ERROR INTROSPECTION (DEBUG ONLY)
# ====================================================

def explain(result: dict) -> str:
    """
    Human-readable debugging helper.
    Safe to use in logs.
    """

    if not isinstance(result, dict):
        return "Invalid result (not dict)"

    status = result.get("status")

    if status == "success":
        return "Execution succeeded"

    error = result.get("error", "Unknown error")
    fix = result.get("fix")

    if fix:
        return f"Failure: {error} | Suggestion: {fix}"

    return f"Failure: {error}"
