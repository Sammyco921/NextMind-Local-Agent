from __future__ import annotations


INJECT_FAILURE_TOOL = "__inject_failure__"


def inject_failure(**kwargs) -> dict:
    raise RuntimeError(
        f"Tool '{INJECT_FAILURE_TOOL}' should never be executed directly. "
        "It is a synthetic node that fails at capability enforcement."
    )
