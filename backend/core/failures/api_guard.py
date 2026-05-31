"""API guard — wraps endpoint handlers with failure normalization.

Ensures all API responses follow the resilience contract:

{
  "result": ...,
  "failure": { "category": "...", "safe_message": "...", ... } | null
}
"""
import functools
import traceback as tb_module

from .taxonomy import FailureRecord, FailureCategory
from .normalizer import normalize_exception
from .degradation import get_degradation_tracker


def failure_response(record: FailureRecord, fallback_result=None) -> dict:
    return {
        "status": "error",
        "result": fallback_result,
        "failure": record.to_dict(),
    }


def ensure_failure_field(data: dict) -> dict:
    if "failure" not in data:
        data["failure"] = None
    return data


def safe_api_call(fn, source_layer: str = "api_server", *args, **kwargs):
    """Execute a callable and return structured response on any exception."""
    try:
        result = fn(*args, **kwargs)
        if isinstance(result, dict):
            ensure_failure_field(result)
        return result
    except Exception as exc:
        record = normalize_exception(exc, source_layer)
        get_degradation_tracker().record(source_layer)
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content=failure_response(record))
