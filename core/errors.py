from dataclasses import dataclass


# ====================================================
# ERROR TYPES
# ====================================================

class ErrorType:
    SUCCESS = "success"
    RETRYABLE_FAIL = "fail"
    FATAL_ERROR = "fatal_error"


# ====================================================
# STANDARD ERROR OBJECT
# ====================================================

@dataclass
class AgentError:
    type: str
    reason: str
    fix: str = None
    step: dict = None


# ====================================================
# FACTORY HELPERS
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
# STATUS CHECKERS
# ====================================================

def is_success(result: dict) -> bool:
    return result.get("status") == ErrorType.SUCCESS


def is_fail(result: dict) -> bool:
    return result.get("status") == ErrorType.RETRYABLE_FAIL


def is_fatal(result: dict) -> bool:
    return result.get("status") == ErrorType.FATAL_ERROR
