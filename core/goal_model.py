# core/goal_model.py

from dataclasses import dataclass
from typing import Dict, Any


# ====================================================
# GOAL MODEL (STRUCTURED INTENT)
# ====================================================

@dataclass
class GoalModel:
    """
    Canonical structured representation of a user goal.

    This is the ONLY input format the planner should accept.
    """

    intent: str
    entities: Dict[str, Any]
    raw: str


# ====================================================
# SAFE CONSTRUCTOR
# ====================================================

def create_goal_model(
    intent: str,
    raw: str,
    entities: Dict[str, Any] | None = None
) -> GoalModel:
    """
    Ensures entities is always initialized safely.
    Prevents None-related downstream crashes.
    """

    return GoalModel(
        intent=intent,
        entities=entities or {},
        raw=raw
    )