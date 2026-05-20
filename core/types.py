# core/types.py
#
# NextMind v0.7 — System Type Contracts
#
# This file defines the strict data shapes used across the pipeline:
#
#   Planner → Validator → Scheduler → Executor
#
# These types are intentionally lightweight and runtime-friendly.
# No enforcement logic lives here—only structure.


from __future__ import annotations

from typing import Dict, List, Optional, TypedDict, Any


# =========================================================
# PLANNER OUTPUT STEP (RAW)
# =========================================================

class PlannerStep(TypedDict, total=False):
    """
    Output of Planner.

    This is intentionally permissive.
    Validation happens downstream.
    """

    tool: str
    args: Dict[str, Any]

    # optional metadata hints
    on_fail: Optional[str]
    fallback: Optional[Dict[str, Any]]
    depends_on: Optional[List[str]]


# =========================================================
# VALIDATED STEP (PIPELINE SAFE)
# =========================================================

class ValidatedStep(TypedDict, total=False):
    """
    Output of PipelineValidator.

    Guaranteed:
      - tool exists
      - args match schema
      - defaults applied
    """

    tool: str
    args: Dict[str, Any]

    meta: Dict[str, Any]  # contains on_fail, fallback, depends_on, etc.


# =========================================================
# SCHEDULED STEP (ORDERED EXECUTION UNIT)
# =========================================================

class ScheduledStep(TypedDict):
    """
    Output of Scheduler.

    Adds execution ordering guarantees.
    """

    id: str
    tool: str
    args: Dict[str, Any]

    meta: Dict[str, Any]

    depends_on: List[str]


# =========================================================
# TRACE ENTRY (EXECUTION LOG)
# =========================================================

class TraceEntry(TypedDict, total=False):
    """
    One executed step record.

    Always included in final execution history.
    """

    step_id: str
    tool: str
    args: Dict[str, Any]

    status: str  # success | fail | soft_fail | skipped

    result: Optional[Dict[str, Any]]
    error: Optional[str]


# =========================================================
# EXECUTION RESULT (FINAL OUTPUT)
# =========================================================

class ExecutionResult(TypedDict):
    """
    Final output returned by Executor / Orchestrator.
    """

    goal: str
    status: str  # success | success_with_warnings | partial_failure | fail

    steps_executed: int
    history: List[TraceEntry]


# =========================================================
# OPTIONAL FUTURE: INTERNAL NODE STATE (NOT USED YET)
# =========================================================

class InternalNodeState(TypedDict, total=False):
    """
    Reserved for future execution graph expansion.

    Do not use in v0.7 runtime yet.
    """

    step_id: str
    status: str
    output: Optional[Dict[str, Any]]
    error: Optional[str]