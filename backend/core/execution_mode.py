# core/execution_mode.py
#
# v1.7: ExecutionMode enum and goal-based mode detection only.
# All mode-specific rules moved to ExecutionSpec (execution_spec.py).

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional


class ExecutionMode(str, Enum):
    NORMAL = "normal"
    STRESS_TEST = "stress_test"
    FAILURE_INJECTION = "failure_injection"

    def __str__(self) -> str:
        return self.value


MODE_KEYWORDS: Dict[str, ExecutionMode] = {
    "stress": ExecutionMode.STRESS_TEST,
    "stress_test": ExecutionMode.STRESS_TEST,
    "stress test": ExecutionMode.STRESS_TEST,
    "failure": ExecutionMode.FAILURE_INJECTION,
    "failure_injection": ExecutionMode.FAILURE_INJECTION,
    "failure injection": ExecutionMode.FAILURE_INJECTION,
}


def detect_mode_from_goal(goal: str) -> Optional[ExecutionMode]:
    lower = (goal or "").strip().lower()
    for keyword, mode in MODE_KEYWORDS.items():
        if keyword in lower:
            return mode
    return None
