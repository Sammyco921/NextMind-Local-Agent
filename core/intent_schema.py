# core/intent_schema.py
from typing import Dict, List


# ====================================================
# INTENT SCHEMA REGISTRY
# ====================================================
# Maps each intent → required entities for execution
# This prevents planner guessing missing data

INTENT_SCHEMA: Dict[str, List[str]] = {

    # ----------------------------
    # FILE OPERATIONS
    # ----------------------------

    "file.create": ["filename", "content"],
    "file.write": ["filename", "content"],
    "file.read": ["filename"],
    "file.delete": ["filename"],

    # ----------------------------
    # DIRECTORY OPERATIONS
    # ----------------------------

    "dir.list": [],

    # ----------------------------
    # PROJECT / ANALYSIS
    # ----------------------------

    "project.summarize": ["path"],
    "project.describe": ["path"],

    # ----------------------------
    # DEFAULT / FALLBACK
    # ----------------------------

    "unknown": []
}


# ====================================================
# HELPER FUNCTIONS
# ====================================================

def get_required_entities(intent: str) -> List[str]:
    """
    Returns required entities for a given intent.
    Defaults to empty list if unknown intent.
    """

    return INTENT_SCHEMA.get(intent, [])


def is_valid_intent(intent: str) -> bool:
    """
    Checks if intent exists in schema registry.
    """

    return intent in INTENT_SCHEMA