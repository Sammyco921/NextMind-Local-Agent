"""CLI guard — wraps CLI entry points with failure normalization.

Never lets raw exceptions or stack traces reach the user.
"""
import sys
import traceback

from .taxonomy import FailureRecord
from .normalizer import normalize_exception
from .degradation import get_degradation_tracker


def safe_cli_call(fn, source_layer: str = "cli", *args, **kwargs):
    """Execute a callable and print structured failure on exception.
    Never prints stack traces.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        record = normalize_exception(exc, source_layer)
        get_degradation_tracker().record(source_layer)
        print(f"[{record.category.value}] {record.safe_message}", file=sys.stderr)
        return None
