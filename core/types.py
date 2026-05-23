# core/types.py
#
# NextMind v0.8 — Shared Pipeline Types
#
# Role:
#   Central definition of all pipeline data structures.
#
# Purpose:
#   - Prevent schema drift between modules
#   - Provide canonical Step + Result definitions
#   - Keep system loosely typed but structurally consistent
#
# Non-goals:
#   - No logic
#   - No validation rules
#   - No execution behavior


from __future__ import annotations

from typing import Dict, Any, List, Optional, TypedDict


# =====================================================
# PLANNER STEP (raw intent output)
# =====================================================

class PlannerStep(TypedDict, total=False):
    tool: str
    args: Dict[str, Any]
    on_fail: Optional[str]
    fallback: Optional[Dict[str, Any]]
    depends_on: List[str]


# =====================================================
# VALIDATED STEP (post-validator contract)
# =====================================================

class ValidatedStep(TypedDict, total=False):
    tool: str
    args: Dict[str, Any]
    on_fail: str
    fallback: Optional[Dict[str, Any]]
    depends_on: List[str]
    meta: Dict[str, Any]


# =====================================================
# SCHEDULED STEP (post-scheduler form)
# =====================================================

class ScheduledStep(TypedDict, total=False):
    _id: str
    tool: str
    args: Dict[str, Any]
    on_fail: str
    fallback: Optional[Dict[str, Any]]
    depends_on: List[str]
    meta: Dict[str, Any]


# =====================================================
# EXECUTION TRACE ENTRY
# =====================================================

class StepTrace(TypedDict, total=False):
    step: Dict[str, Any]
    result: Dict[str, Any]
    note: Optional[str]


# =====================================================
# EXECUTION RESULT
# =====================================================

class ExecutionResultDict(TypedDict, total=False):
    goal: str
    status: str
    steps_executed: int
    history: List[StepTrace]